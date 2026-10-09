import pandas as pd
import pandas_ta as ta
from pydantic import BaseModel, Field

from app.strategies.indicators import compute_regime
from app.strategies.types import Signal, SignalAction, StrategyContext, StrategyMetadata, StrategyTemplate


class BbMeanRevertParams(BaseModel):
    period: int = Field(20, ge=10, le=50)
    std_dev: float = Field(2.0, ge=1.5, le=3.0)
    adx_max: float = Field(20.0, ge=10.0, le=25.0)
    stop_loss_pct: float = Field(1.0, ge=0.5, le=8.0)
    take_profit_pct: float = Field(2.0, ge=1.0, le=15.0)
    position_pct: float = Field(20.0, ge=5.0, le=100.0)


class BbMeanRevertStrategy(StrategyTemplate):
    metadata = StrategyMetadata(
        id="bb_mean_revert",
        name="Bollinger Mean Revert",
        description="Buy lower band / exit mid-upper band when ADX indicates range.",
        category="mean_reversion",
        supported_timeframes=["5m", "15m", "1h", "4h"],
    )
    params_model = BbMeanRevertParams

    def warmup_bars(self, params: BbMeanRevertParams) -> int:
        return params.period + 10

    def on_bar(self, ctx: StrategyContext, params: BbMeanRevertParams) -> Signal | None:
        if len(ctx.bars) < self.warmup_bars(params):
            return None
        df = ctx.bars
        bb = ta.bbands(df["close"], length=params.period, std=params.std_dev)
        if bb is None or bb.empty:
            return None
        lower_col = [c for c in bb.columns if c.startswith("BBL")][0]
        mid_col = [c for c in bb.columns if c.startswith("BBM")][0]
        upper_col = [c for c in bb.columns if c.startswith("BBU")][0]
        row = df.iloc[-1]
        regime = compute_regime(row)
        adx = regime.get("adx")
        if adx is None or adx > params.adx_max:
            return None
        if regime.get("label") not in ("range", "neutral"):
            return None

        close = row["close"]
        lower = bb[lower_col].iloc[-1]
        mid = bb[mid_col].iloc[-1]
        upper = bb[upper_col].iloc[-1]
        if any(pd.isna(x) for x in (close, lower, mid, upper)):
            return None

        if ctx.position_qty <= 0 and close <= lower:
            return Signal(
                action=SignalAction.buy,
                reason="Price at lower Bollinger band in range regime",
                stop_loss_pct=params.stop_loss_pct,
                take_profit_pct=params.take_profit_pct,
                metadata={"regime": regime, "position_pct": params.position_pct},
            )
        if ctx.position_qty > 0 and (close >= mid or close >= upper):
            return Signal(
                action=SignalAction.close,
                reason="Mean reversion target (BB mid/upper)",
                metadata={"regime": regime},
            )
        return None
