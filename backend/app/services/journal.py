from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JournalEvent, JournalEventType, Run
from app.engine.events import StreamEvent, event_bus
from app.services.decision_log import _json_native


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def regime_signature(regime: dict[str, Any]) -> str:
    label = regime.get("label") or "neutral"
    trend = regime.get("trend") or "neutral"
    return f"{label}|{trend}"


def regime_table_payload(
    *,
    symbol: str,
    timeframe: str,
    candle_open_time: int,
    regime: dict[str, Any],
) -> dict[str, Any]:
    return _json_native(
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "candle_open_time": candle_open_time,
            "trend": regime.get("trend"),
            "regime": regime.get("label"),
            "adx": regime.get("adx"),
            "atr_pct": regime.get("atr_pct"),
            "close": regime.get("close"),
            "regime_snapshot": regime,
        }
    )


async def try_log_journal(
    session: AsyncSession,
    run: Run,
    event_type: JournalEventType,
    message: str,
    payload: dict[str, Any] | None = None,
    *,
    dedupe_key: str | None = None,
    bot_id: int | None = None,
) -> JournalEvent | None:
    if dedupe_key:
        existing = await session.execute(
            select(JournalEvent.id).where(
                JournalEvent.run_id == run.id,
                JournalEvent.dedupe_key == dedupe_key,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return None

    ev = JournalEvent(
        run_id=run.id,
        bot_id=bot_id or run.bot_id,
        event_type=event_type,
        message=message,
        payload=_json_native(payload or {}),
        dedupe_key=dedupe_key,
        created_at=_utcnow(),
    )
    session.add(ev)
    await session.flush()

    await event_bus.publish(
        StreamEvent(
            type="journal",
            payload={
                "run_id": run.id,
                "bot_id": ev.bot_id,
                "event_type": event_type.value,
                "message": message,
                "id": ev.id,
            },
        )
    )
    return ev


async def log_regime_if_changed(
    session: AsyncSession,
    run: Run,
    bot_id: int,
    symbol: str,
    timeframe: str,
    candle_open_time: int,
    regime: dict[str, Any],
) -> JournalEvent | None:
    bar_dedupe = f"regime_bar:{candle_open_time}"
    existing = await session.execute(
        select(JournalEvent.id).where(
            JournalEvent.run_id == run.id,
            JournalEvent.dedupe_key == bar_dedupe,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return None

    sig = regime_signature(regime)
    if run.last_regime_signature == sig:
        return None

    run.last_regime_signature = sig
    return await try_log_journal(
        session,
        run,
        JournalEventType.regime_change,
        f"Regime → {regime.get('label', 'neutral')} ({regime.get('trend', 'neutral')})",
        regime_table_payload(
            symbol=symbol,
            timeframe=timeframe,
            candle_open_time=candle_open_time,
            regime=regime,
        ),
        dedupe_key=bar_dedupe,
        bot_id=bot_id,
    )


async def log_strategy_evaluation(
    session: AsyncSession,
    run: Run,
    bot_id: int,
    *,
    candle_open_time: int,
    decision: str,
    reason: str,
    symbol: str,
    timeframe: str,
    indicators: dict[str, Any],
    rejection_source: str | None = None,
    rejection_detail: str | None = None,
) -> None:
    dedupe = f"eval:{candle_open_time}"
    payload = {
        "candle_open_time": candle_open_time,
        "symbol": symbol,
        "timeframe": timeframe,
        "decision": decision,
        "reason": reason,
        "indicators": indicators,
        "rejection_source": rejection_source,
        "rejection_detail": rejection_detail,
    }
    await try_log_journal(
        session,
        run,
        JournalEventType.strategy_evaluation,
        f"Evaluation: {decision} — {reason}",
        payload,
        dedupe_key=dedupe,
        bot_id=bot_id,
    )
    await try_log_journal(
        session,
        run,
        JournalEventType.decision,
        reason,
        {"candle_open_time": candle_open_time, "decision": decision, "reason": reason},
        dedupe_key=f"decision:{candle_open_time}",
        bot_id=bot_id,
    )
