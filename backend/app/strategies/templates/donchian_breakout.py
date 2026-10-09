import pandas as pd
from pydantic import BaseModel, Field

from app.strategies.indicators import compute_regime
from app.strategies.types import Signal, SignalAction, StrategyContext, StrategyMetadata, StrategyTemplate


class DonchianBreakoutParams(BaseModel):
    channel_period: int = Field(20, ge=10, le=55)
    max_atr_pct: float = Field(3.5, ge=1.0, le=8.0)
    atr_stop_mult: float = Field(2.0, ge=1.0, le=5.0)
    take_profit_pct: float = Field(4.0, ge=1.0, le=25.0)
    position_pct: float = Field(22.0, ge=5.0, le=100.0)


class DonchianBreakoutStrategy(StrategyTemplate):
    metadata = StrategyMetadata(
        id="donchian_breakout",
        name="Donchian Breakout",
        description="Breakout above channel with ATR volatility cap and ATR-based stop.",
        category="breakout",
        supported_timeframes=["15m", "1h", "4h"],
    )
    params_model = DonchianBreakoutParams

    def warmup_bars(self, params: DonchianBreakoutParams) -> int:
        return params.channel_period + 5

    def on_bar(self, ctx: StrategyContext, params: DonchianBreakoutParams) -> Signal | None:
        if len(ctx.bars) < self.warmup_bars(params):
            return None
        df = ctx.bars
        row = df.iloc[-1]
        prev = df.iloc[-2]
        regime = compute_regime(row)
        atr_pct = regime.get("atr_pct")
        if atr_pct is not None and atr_pct > params.max_atr_pct:
            return None

        high_col = df["high"].rolling(params.channel_period).max()
        low_col = df["low"].rolling(params.channel_period).min()
        prev_upper = high_col.iloc[-2]
        close = row["close"]
        if pd.isna(prev_upper) or pd.isna(close):
            return None

        atr = row.get("atr")
        stop_pct = params.take_profit_pct
        if pd.notna(atr) and close:
            stop_pct = float(atr / close * 100 * params.atr_stop_mult)

        if ctx.position_qty <= 0 and close > prev_upper:
            return Signal(
                action=SignalAction.buy,
                reason="Donchian upper breakout",
                stop_loss_pct=stop_pct,
                take_profit_pct=params.take_profit_pct,
                metadata={"regime": regime, "position_pct": params.position_pct},
            )
        lower = low_col.iloc[-1]
        if ctx.position_qty > 0 and pd.notna(lower) and close < lower:
            return Signal(
                action=SignalAction.close,
                reason="Donchian lower channel exit",
                metadata={"regime": regime},
            )
        return None
