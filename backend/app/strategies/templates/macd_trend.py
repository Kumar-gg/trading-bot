import pandas as pd
import pandas_ta as ta
from pydantic import BaseModel, Field

from app.strategies.indicators import compute_regime
from app.strategies.types import Signal, SignalAction, StrategyContext, StrategyMetadata, StrategyTemplate


class MacdTrendParams(BaseModel):
    fast: int = Field(12, ge=5, le=20)
    slow: int = Field(26, ge=15, le=50)
    signal: int = Field(9, ge=5, le=15)
    ema_filter: int = Field(200, ge=50, le=300)
    adx_threshold: float = Field(20.0, ge=10.0, le=50.0)
    stop_loss_pct: float = Field(1.5, ge=0.5, le=10.0)
    take_profit_pct: float = Field(3.0, ge=1.0, le=20.0)
    position_pct: float = Field(25.0, ge=5.0, le=100.0)


def _macd_cols(macd: pd.DataFrame) -> tuple[str, str]:
    line_col = next(c for c in macd.columns if c.startswith("MACD_"))
    sig_col = next(c for c in macd.columns if c.startswith("MACDs"))
    return line_col, sig_col


class MacdTrendStrategy(StrategyTemplate):
    metadata = StrategyMetadata(
        id="macd_trend",
        name="MACD Trend",
        description="MACD line/signal cross with EMA trend filter and ADX.",
        category="trend",
        supported_timeframes=["5m", "15m", "1h", "4h"],
    )
    params_model = MacdTrendParams

    def warmup_bars(self, params: MacdTrendParams) -> int:
        return max(params.slow, params.ema_filter) + params.signal + 5

    def on_bar(self, ctx: StrategyContext, params: MacdTrendParams) -> Signal | None:
        if len(ctx.bars) < self.warmup_bars(params):
            return None
        close = ctx.bars["close"]
        macd = ta.macd(close, fast=params.fast, slow=params.slow, signal=params.signal)
        ema = ta.ema(close, length=params.ema_filter)
        if macd is None or macd.empty or ema is None:
            return None
        try:
            line_col, sig_col = _macd_cols(macd)
        except StopIteration:
            return None
        line = macd[line_col]
        signal_line = macd[sig_col]
        row = ctx.bars.iloc[-1]
        regime = compute_regime(row)
        adx = regime.get("adx")
        if adx is None or adx < params.adx_threshold:
            return None

        ml, ms = line.iloc[-1], signal_line.iloc[-1]
        pml, pms = line.iloc[-2], signal_line.iloc[-2]
        ema_v = ema.iloc[-1]
        price = row["close"]
        if any(pd.isna(x) for x in (ml, ms, pml, pms, ema_v, price)):
            return None

        cross_up = pml <= pms and ml > ms
        cross_down = pml >= pms and ml < ms

        if ctx.position_qty <= 0 and cross_up and price > ema_v:
            return Signal(
                action=SignalAction.buy,
                reason="MACD bullish cross above EMA filter",
                stop_loss_pct=params.stop_loss_pct,
                take_profit_pct=params.take_profit_pct,
                metadata={"regime": regime, "position_pct": params.position_pct},
            )
        if ctx.position_qty > 0 and cross_down:
            return Signal(
                action=SignalAction.close,
                reason="MACD bearish cross exit",
                metadata={"regime": regime},
            )
        return None
