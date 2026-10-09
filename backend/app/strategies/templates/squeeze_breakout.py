import pandas as pd
import pandas_ta as ta
from pydantic import BaseModel, Field

from app.strategies.indicators import compute_regime
from app.strategies.types import Signal, SignalAction, StrategyContext, StrategyMetadata, StrategyTemplate


class SqueezeBreakoutParams(BaseModel):
    bb_length: int = Field(20, ge=10, le=40)
    bb_std: float = Field(2.0, ge=1.5, le=3.0)
    kc_length: int = Field(20, ge=10, le=40)
    kc_scalar: float = Field(1.5, ge=1.0, le=2.5)
    squeeze_bars_min: int = Field(3, ge=1, le=20)
    atr_stop_mult: float = Field(2.0, ge=1.0, le=5.0)
    max_atr_pct: float = Field(4.0, ge=2.0, le=8.0)
    take_profit_pct: float = Field(4.0, ge=1.0, le=25.0)
    position_pct: float = Field(22.0, ge=5.0, le=100.0)


class SqueezeBreakoutStrategy(StrategyTemplate):
    metadata = StrategyMetadata(
        id="squeeze_breakout",
        name="Squeeze Breakout",
        description="TTM-style squeeze (BB inside KC) then momentum breakout.",
        category="volatility",
        supported_timeframes=["15m", "1h", "4h"],
    )
    params_model = SqueezeBreakoutParams

    def warmup_bars(self, params: SqueezeBreakoutParams) -> int:
        return max(params.bb_length, params.kc_length) + params.squeeze_bars_min + 5

    def _squeeze_series(self, df: pd.DataFrame, params: SqueezeBreakoutParams) -> pd.Series:
        bb = ta.bbands(df["close"], length=params.bb_length, std=params.bb_std)
        kc = ta.kc(df["high"], df["low"], df["close"], length=params.kc_length, scalar=params.kc_scalar)
        if bb is None or kc is None or bb.empty or kc.empty:
            return pd.Series([False] * len(df))
        bb_u = [c for c in bb.columns if c.startswith("BBU")][0]
        bb_l = [c for c in bb.columns if c.startswith("BBL")][0]
        kc_u = next(c for c in kc.columns if "KCU" in c.upper())
        kc_l = next(c for c in kc.columns if "KCL" in c.upper())
        return (bb[bb_u] < kc[kc_u]) & (bb[bb_l] > kc[kc_l])

    def on_bar(self, ctx: StrategyContext, params: SqueezeBreakoutParams) -> Signal | None:
        if len(ctx.bars) < self.warmup_bars(params):
            return None
        df = ctx.bars
        row = df.iloc[-1]
        regime = compute_regime(row)
        atr_pct = regime.get("atr_pct")
        if atr_pct is not None and atr_pct > params.max_atr_pct:
            return None

        squeeze = self._squeeze_series(df, params)
        if len(squeeze) < params.squeeze_bars_min + 2:
            return None
        was_squeeze = bool(squeeze.iloc[-(params.squeeze_bars_min + 1) : -1].all())
        now_expanding = not bool(squeeze.iloc[-1])
        close = row["close"]
        prev_close = df.iloc[-2]["close"]
        atr = row.get("atr")
        stop_pct = params.take_profit_pct
        if pd.notna(atr) and pd.notna(close) and close:
            stop_pct = float(atr / close * 100 * params.atr_stop_mult)

        if ctx.position_qty <= 0 and was_squeeze and now_expanding and close > prev_close:
            return Signal(
                action=SignalAction.buy,
                reason="Volatility squeeze release breakout",
                stop_loss_pct=stop_pct,
                take_profit_pct=params.take_profit_pct,
                metadata={"regime": regime, "position_pct": params.position_pct},
            )
        if ctx.position_qty > 0 and now_expanding and close < prev_close:
            return Signal(
                action=SignalAction.close,
                reason="Squeeze breakdown exit",
                metadata={"regime": regime},
            )
        return None
