import pandas as pd
import pandas_ta as ta
from pydantic import BaseModel, Field

from app.strategies.indicators import compute_regime
from app.strategies.types import Signal, SignalAction, StrategyContext, StrategyMetadata, StrategyTemplate


class SupertrendTrailParams(BaseModel):
    atr_length: int = Field(10, ge=7, le=21)
    multiplier: float = Field(3.0, ge=2.0, le=5.0)
    ema_filter: int = Field(50, ge=20, le=200)
    use_ema_filter: bool = Field(True)
    stop_loss_pct: float = Field(2.0, ge=0.5, le=10.0)
    take_profit_pct: float = Field(6.0, ge=2.0, le=30.0)
    position_pct: float = Field(25.0, ge=5.0, le=100.0)


class SupertrendTrailStrategy(StrategyTemplate):
    metadata = StrategyMetadata(
        id="supertrend_trail",
        name="Supertrend Trail",
        description="Supertrend direction flips for entry/exit with optional EMA filter.",
        category="trend",
        supported_timeframes=["5m", "15m", "1h", "4h"],
    )
    params_model = SupertrendTrailParams

    def warmup_bars(self, params: SupertrendTrailParams) -> int:
        return max(params.atr_length, params.ema_filter if params.use_ema_filter else 0) + 10

    def on_bar(self, ctx: StrategyContext, params: SupertrendTrailParams) -> Signal | None:
        if len(ctx.bars) < self.warmup_bars(params):
            return None
        df = ctx.bars
        st = ta.supertrend(df["high"], df["low"], df["close"], length=params.atr_length, multiplier=params.multiplier)
        if st is None or st.empty:
            return None
        dir_col = [c for c in st.columns if c.startswith("SUPERTd")][0]
        direction = st[dir_col]
        row = df.iloc[-1]
        regime = compute_regime(row)
        d = direction.iloc[-1]
        pd_prev = direction.iloc[-2]
        if pd.isna(d) or pd.isna(pd_prev):
            return None

        close = row["close"]
        if params.use_ema_filter:
            ema = ta.ema(df["close"], length=params.ema_filter)
            if ema is None or pd.isna(ema.iloc[-1]):
                return None
            if close < ema.iloc[-1] and ctx.position_qty <= 0:
                return None

        flip_bull = pd_prev < 0 and d > 0
        flip_bear = pd_prev > 0 and d < 0

        if ctx.position_qty <= 0 and flip_bull:
            return Signal(
                action=SignalAction.buy,
                reason="Supertrend flipped bullish",
                stop_loss_pct=params.stop_loss_pct,
                take_profit_pct=params.take_profit_pct,
                metadata={"regime": regime, "position_pct": params.position_pct},
            )
        if ctx.position_qty > 0 and flip_bear:
            return Signal(
                action=SignalAction.close,
                reason="Supertrend flipped bearish",
                metadata={"regime": regime},
            )
        return None
