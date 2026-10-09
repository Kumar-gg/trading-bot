import pandas as pd
import pandas_ta as ta
from pydantic import BaseModel, Field

from app.strategies.indicators import compute_regime
from app.strategies.types import Signal, SignalAction, StrategyContext, StrategyMetadata, StrategyTemplate


class EmaTrendParams(BaseModel):
    ema_fast: int = Field(12, ge=5, le=50)
    ema_slow: int = Field(26, ge=10, le=200)
    adx_threshold: float = Field(20.0, ge=10.0, le=50.0)
    stop_loss_pct: float = Field(1.5, ge=0.5, le=10.0)
    take_profit_pct: float = Field(3.0, ge=1.0, le=20.0)
    position_pct: float = Field(25.0, ge=5.0, le=100.0)


class EmaTrendStrategy(StrategyTemplate):
    metadata = StrategyMetadata(
        id="ema_trend",
        name="EMA Trend",
        description="EMA crossover with ADX trend filter.",
        category="trend",
        supported_timeframes=["1m", "5m", "15m", "1h", "4h"],
    )
    params_model = EmaTrendParams

    def warmup_bars(self, params: EmaTrendParams) -> int:
        return max(params.ema_slow, 30) + 5

    def on_bar(self, ctx: StrategyContext, params: EmaTrendParams) -> Signal | None:
        if len(ctx.bars) < self.warmup_bars(params):
            return None
        close = ctx.bars["close"]
        fast = ta.ema(close, length=params.ema_fast)
        slow = ta.ema(close, length=params.ema_slow)
        if fast is None or slow is None:
            return None
        row = ctx.bars.iloc[-1]
        regime = compute_regime(row)
        adx = regime.get("adx")
        if adx is None or adx < params.adx_threshold:
            return None

        f, s = fast.iloc[-1], slow.iloc[-1]
        pf, ps = fast.iloc[-2], slow.iloc[-2]
        if any(pd.isna(x) for x in (f, s, pf, ps)):
            return None

        cross_up = pf <= ps and f > s
        cross_down = pf >= ps and f < s

        if ctx.position_qty <= 0 and cross_up and regime["trend"] == "bull":
            return Signal(
                action=SignalAction.buy,
                reason="EMA bullish cross with ADX filter",
                stop_loss_pct=params.stop_loss_pct,
                take_profit_pct=params.take_profit_pct,
                metadata={"regime": regime, "position_pct": params.position_pct},
            )
        if ctx.position_qty > 0 and cross_down:
            return Signal(
                action=SignalAction.close,
                reason="EMA bearish cross exit",
                metadata={"regime": regime},
            )
        return None
