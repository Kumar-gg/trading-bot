from dataclasses import asdict, dataclass
from typing import Any

from pydantic import BaseModel

from app.strategies.types import StrategyContext


@dataclass
class ConditionCheck:
    name: str
    passed: bool
    detail: str = ""
    kind: str = "entry"  # entry | exit | filter

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["passed"] = bool(d["passed"])
        return d


def indicator_snapshot(ctx: StrategyContext) -> dict[str, Any]:
    if ctx.bars.empty:
        return {}
    row = ctx.bars.iloc[-1]
    keys = (
        "close",
        "ema_fast",
        "ema_slow",
        "rsi",
        "adx",
        "atr",
        "donchian_high",
        "donchian_low",
    )
    out: dict[str, Any] = {}
    for k in keys:
        if k in row.index:
            v = row[k]
            if v == v:  # not NaN
                out[k] = float(v)
    out["regime"] = ctx.regime
    return out


def audit_template(template_id: str, ctx: StrategyContext, params: BaseModel) -> list[ConditionCheck]:
    from app.strategies import auditors

    fn = auditors.AUDITORS.get(template_id)
    if fn is None:
        return [
            ConditionCheck(
                name="strategy_audit",
                passed=True,
                detail="No detailed audit for this template",
                kind="filter",
            )
        ]
    return fn(ctx, params)
