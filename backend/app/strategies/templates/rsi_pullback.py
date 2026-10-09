import pandas as pd
from pydantic import BaseModel, Field

from app.strategies.indicators import compute_regime
from app.strategies.types import Signal, SignalAction, StrategyContext, StrategyMetadata, StrategyTemplate


class RsiPullbackParams(BaseModel):
    rsi_period: int = Field(14, ge=5, le=30)
    rsi_oversold: float = Field(35.0, ge=20.0, le=45.0)
    rsi_overbought: float = Field(65.0, ge=55.0, le=80.0)
    adx_min: float = Field(18.0, ge=10.0, le=40.0)
    adx_max: float = Field(45.0, ge=25.0, le=60.0)
    stop_loss_pct: float = Field(1.2, ge=0.5, le=10.0)
    take_profit_pct: float = Field(2.5, ge=1.0, le=20.0)
    position_pct: float = Field(20.0, ge=5.0, le=100.0)


class RsiPullbackStrategy(StrategyTemplate):
    metadata = StrategyMetadata(
        id="rsi_pullback",
        name="RSI Pullback",
        description="RSI pullback entries in established trends (ADX band filter).",
        category="trend",
        supported_timeframes=["5m", "15m", "1h", "4h"],
    )
    params_model = RsiPullbackParams

    def warmup_bars(self, params: RsiPullbackParams) -> int:
        return max(params.rsi_period, 30) + 5

    def on_bar(self, ctx: StrategyContext, params: RsiPullbackParams) -> Signal | None:
        if len(ctx.bars) < self.warmup_bars(params):
            return None
        row = ctx.bars.iloc[-1]
        regime = compute_regime(row)
        adx = regime.get("adx")
        if adx is None or adx < params.adx_min or adx > params.adx_max:
            return None
        rsi = row.get("rsi")
        if pd.isna(rsi):
            return None

        if ctx.position_qty <= 0 and regime["trend"] == "bull" and rsi <= params.rsi_oversold:
            return Signal(
                action=SignalAction.buy,
                reason="RSI oversold pullback in bull trend",
                stop_loss_pct=params.stop_loss_pct,
                take_profit_pct=params.take_profit_pct,
                metadata={"regime": regime, "position_pct": params.position_pct, "rsi": float(rsi)},
            )
        if ctx.position_qty > 0 and rsi >= params.rsi_overbought:
            return Signal(
                action=SignalAction.close,
                reason="RSI overbought exit",
                metadata={"regime": regime, "rsi": float(rsi)},
            )
        return None
