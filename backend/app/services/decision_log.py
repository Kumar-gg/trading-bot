import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Bot, DecisionLog, DecisionType, Run
from app.engine.events import StreamEvent, event_bus
from app.services.health import refresh_bot_health
from app.strategies.audit import audit_template, indicator_snapshot
from app.strategies.types import Signal, SignalAction


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_native(obj: Any) -> Any:
    if hasattr(obj, "item") and callable(obj.item):
        obj = obj.item()
    if isinstance(obj, dict):
        return {k: _json_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_native(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def _split_conditions(checks: list) -> tuple[list[dict], list[dict]]:
    entry = [c.to_dict() for c in checks if c.kind == "entry"]
    exit_c = [c.to_dict() for c in checks if c.kind == "exit"]
    filters = [c.to_dict() for c in checks if c.kind == "filter"]
    return entry + filters, exit_c


async def record_decision(
    session: AsyncSession,
    bot: Bot,
    run: Run,
    *,
    candle_open_time: int | None,
    symbol_price: float | None,
    btc_price: float | None,
    market_data_age_sec: float | None,
    checks: list,
    decision: DecisionType,
    reason: str,
    rejection_source: str | None = None,
    rejection_detail: str | None = None,
    indicators: dict[str, Any] | None = None,
) -> DecisionLog:
    entry, exit_c = _split_conditions(checks)
    row = DecisionLog(
        bot_id=bot.id,
        run_id=run.id,
        evaluated_at=_utcnow(),
        candle_open_time=candle_open_time,
        symbol_price=symbol_price,
        btc_price=btc_price,
        market_data_age_sec=market_data_age_sec,
        indicators=_json_native(indicators or {}),
        entry_conditions=_json_native(entry),
        exit_conditions=_json_native(exit_c),
        decision=decision,
        reason=reason,
        rejection_source=rejection_source,
        rejection_detail=rejection_detail,
    )
    session.add(row)
    bot.last_evaluation_at = row.evaluated_at
    bot.latest_decision = decision
    bot.latest_decision_reason = reason
    if rejection_source:
        bot.last_eval_error = rejection_detail or reason
    else:
        bot.last_eval_error = None
    refresh_bot_health(bot, market_data_age_sec, now=row.evaluated_at)
    await session.flush()
    await event_bus.publish(
        StreamEvent(
            type="decision",
            payload={
                "bot_id": bot.id,
                "decision": decision.value,
                "reason": reason,
                "evaluated_at": row.evaluated_at.isoformat(),
            },
        )
    )
    return row


def decision_from_signal(signal: Signal | None) -> DecisionType:
    if signal is None:
        return DecisionType.HOLD
    if signal.action == SignalAction.buy:
        return DecisionType.BUY
    if signal.action in (SignalAction.sell, SignalAction.close):
        return DecisionType.SELL
    return DecisionType.HOLD


def build_checks_and_indicators(template_id: str, ctx, params) -> tuple[list, dict]:
    if not ctx.bars.empty:
        from app.strategies.indicators import compute_regime

        ctx.regime = compute_regime(ctx.bars.iloc[-1])
    checks = audit_template(template_id, ctx, params)
    indicators = indicator_snapshot(ctx)
    return checks, indicators
