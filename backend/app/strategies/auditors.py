"""Read-only condition audits mirroring strategy rules (does not place trades)."""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta

from app.strategies.audit import ConditionCheck
from app.strategies.indicators import compute_regime
from app.strategies.templates.bb_mean_revert import BbMeanRevertParams
from app.strategies.templates.donchian_breakout import DonchianBreakoutParams
from app.strategies.templates.ema_trend import EmaTrendParams
from app.strategies.templates.macd_trend import MacdTrendParams
from app.strategies.templates.rsi_pullback import RsiPullbackParams
from app.strategies.templates.squeeze_breakout import SqueezeBreakoutParams
from app.strategies.templates.supertrend_trail import SupertrendTrailParams
from app.strategies.types import StrategyContext


def _warmup(name: str, ok: bool, need: int, have: int) -> ConditionCheck:
    return ConditionCheck(
        name=name,
        passed=ok,
        detail=f"bars {have}/{need}",
        kind="filter",
    )


def audit_ema_trend(ctx: StrategyContext, params: EmaTrendParams) -> list[ConditionCheck]:
    need = max(params.ema_slow, 30) + 5
    checks: list[ConditionCheck] = [
        _warmup("warmup_bars", len(ctx.bars) >= need, need, len(ctx.bars)),
    ]
    if not checks[0].passed:
        return checks
    close = ctx.bars["close"]
    fast = ta.ema(close, length=params.ema_fast)
    slow = ta.ema(close, length=params.ema_slow)
    row = ctx.bars.iloc[-1]
    regime = compute_regime(row)
    ctx.regime = regime
    adx = regime.get("adx")
    checks.append(
        ConditionCheck(
            "adx_above_threshold",
            adx is not None and adx >= params.adx_threshold,
            f"ADX={adx}, need>={params.adx_threshold}",
            "filter",
        )
    )
    if fast is None or slow is None:
        return checks
    f, s = fast.iloc[-1], slow.iloc[-1]
    pf, ps = fast.iloc[-2], slow.iloc[-2]
    cross_up = pf <= ps and f > s
    cross_down = pf >= ps and f < s
    in_pos = (ctx.position_qty or 0) > 0
    checks.append(
        ConditionCheck(
            "entry_ema_bull_cross",
            not in_pos and cross_up and regime.get("trend") == "bull",
            f"cross_up={cross_up}, trend={regime.get('trend')}",
            "entry",
        )
    )
    checks.append(
        ConditionCheck(
            "exit_ema_bear_cross",
            in_pos and cross_down,
            f"cross_down={cross_down}",
            "exit",
        )
    )
    return checks


def audit_rsi_pullback(ctx: StrategyContext, params: RsiPullbackParams) -> list[ConditionCheck]:
    need = max(params.rsi_period, 30) + 5
    checks = [_warmup("warmup_bars", len(ctx.bars) >= need, need, len(ctx.bars))]
    if not checks[0].passed:
        return checks
    row = ctx.bars.iloc[-1]
    regime = compute_regime(row)
    adx = regime.get("adx")
    rsi = row.get("rsi")
    in_pos = (ctx.position_qty or 0) > 0
    checks.extend(
        [
            ConditionCheck(
                "adx_in_band",
                adx is not None and params.adx_min <= adx <= params.adx_max,
                f"ADX={adx}",
                "filter",
            ),
            ConditionCheck(
                "entry_rsi_oversold_in_bull",
                not in_pos
                and regime.get("trend") == "bull"
                and pd.notna(rsi)
                and rsi <= params.rsi_oversold,
                f"RSI={rsi}, trend={regime.get('trend')}",
                "entry",
            ),
            ConditionCheck(
                "exit_rsi_overbought",
                in_pos and pd.notna(rsi) and rsi >= params.rsi_overbought,
                f"RSI={rsi}",
                "exit",
            ),
        ]
    )
    return checks


def audit_donchian(ctx: StrategyContext, params: DonchianBreakoutParams) -> list[ConditionCheck]:
    need = params.channel_period + 5
    checks = [_warmup("warmup_bars", len(ctx.bars) >= need, need, len(ctx.bars))]
    if not checks[0].passed:
        return checks
    df = ctx.bars
    row = df.iloc[-1]
    regime = compute_regime(row)
    atr_pct = regime.get("atr_pct")
    high_col = df["high"].rolling(params.channel_period).max()
    low_col = df["low"].rolling(params.channel_period).min()
    prev_upper = high_col.iloc[-2]
    close = row["close"]
    in_pos = (ctx.position_qty or 0) > 0
    checks.extend(
        [
            ConditionCheck(
                "atr_vol_cap",
                atr_pct is None or atr_pct <= params.max_atr_pct,
                f"ATR%={atr_pct}",
                "filter",
            ),
            ConditionCheck(
                "entry_breakout_upper",
                not in_pos and pd.notna(prev_upper) and close > prev_upper,
                f"close={close}, prev_upper={prev_upper}",
                "entry",
            ),
            ConditionCheck(
                "exit_break_below_lower",
                in_pos and pd.notna(low_col.iloc[-1]) and close < low_col.iloc[-1],
                f"close={close}",
                "exit",
            ),
        ]
    )
    return checks


def audit_macd(ctx: StrategyContext, params: MacdTrendParams) -> list[ConditionCheck]:
    need = max(params.slow, params.ema_filter) + params.signal + 5
    checks = [_warmup("warmup_bars", len(ctx.bars) >= need, need, len(ctx.bars))]
    if not checks[0].passed:
        return checks
    close = ctx.bars["close"]
    macd = ta.macd(close, fast=params.fast, slow=params.slow, signal=params.signal)
    ema = ta.ema(close, length=params.ema_filter)
    row = ctx.bars.iloc[-1]
    regime = compute_regime(row)
    adx = regime.get("adx")
    checks.append(
        ConditionCheck(
            "adx_above_threshold",
            adx is not None and adx >= params.adx_threshold,
            f"ADX={adx}",
            "filter",
        )
    )
    if macd is None or ema is None:
        return checks
    line_col = next(c for c in macd.columns if c.startswith("MACD_"))
    sig_col = next(c for c in macd.columns if c.startswith("MACDs"))
    ml, ms = macd[line_col].iloc[-1], macd[sig_col].iloc[-1]
    pml, pms = macd[line_col].iloc[-2], macd[sig_col].iloc[-2]
    cross_up = pml <= pms and ml > ms
    cross_down = pml >= pms and ml < ms
    price = row["close"]
    in_pos = (ctx.position_qty or 0) > 0
    checks.extend(
        [
            ConditionCheck(
                "entry_macd_cross_above_ema",
                not in_pos and cross_up and pd.notna(ema.iloc[-1]) and price > ema.iloc[-1],
                f"cross_up={cross_up}, price>{ema.iloc[-1]}",
                "entry",
            ),
            ConditionCheck(
                "exit_macd_bear_cross",
                in_pos and cross_down,
                f"cross_down={cross_down}",
                "exit",
            ),
        ]
    )
    return checks


def audit_bb(ctx: StrategyContext, params: BbMeanRevertParams) -> list[ConditionCheck]:
    need = params.period + 10
    checks = [_warmup("warmup_bars", len(ctx.bars) >= need, need, len(ctx.bars))]
    if not checks[0].passed:
        return checks
    bb = ta.bbands(ctx.bars["close"], length=params.period, std=params.std_dev)
    row = ctx.bars.iloc[-1]
    regime = compute_regime(row)
    adx = regime.get("adx")
    in_pos = (ctx.position_qty or 0) > 0
    close = row["close"]
    checks.extend(
        [
            ConditionCheck(
                "range_regime_adx",
                adx is not None and adx <= params.adx_max,
                f"ADX={adx}",
                "filter",
            ),
            ConditionCheck(
                "regime_label_range",
                regime.get("label") in ("range", "neutral"),
                f"label={regime.get('label')}",
                "filter",
            ),
        ]
    )
    if bb is None or bb.empty:
        return checks
    lower = bb[[c for c in bb.columns if c.startswith("BBL")][0]].iloc[-1]
    mid = bb[[c for c in bb.columns if c.startswith("BBM")][0]].iloc[-1]
    upper = bb[[c for c in bb.columns if c.startswith("BBU")][0]].iloc[-1]
    checks.extend(
        [
            ConditionCheck(
                "entry_at_lower_band",
                not in_pos and pd.notna(lower) and close <= lower,
                f"close={close}, lower={lower}",
                "entry",
            ),
            ConditionCheck(
                "exit_at_mid_or_upper",
                in_pos and pd.notna(mid) and (close >= mid or close >= upper),
                f"close={close}, mid={mid}",
                "exit",
            ),
        ]
    )
    return checks


def audit_squeeze(ctx: StrategyContext, params: SqueezeBreakoutParams) -> list[ConditionCheck]:
    from app.strategies.templates.squeeze_breakout import SqueezeBreakoutStrategy

    st = SqueezeBreakoutStrategy()
    need = st.warmup_bars(params)
    checks = [_warmup("warmup_bars", len(ctx.bars) >= need, need, len(ctx.bars))]
    if not checks[0].passed:
        return checks
    df = ctx.bars
    row = df.iloc[-1]
    regime = compute_regime(row)
    squeeze = st._squeeze_series(df, params)
    was_squeeze = bool(squeeze.iloc[-(params.squeeze_bars_min + 1) : -1].all())
    now_expanding = not bool(squeeze.iloc[-1])
    close = row["close"]
    prev_close = df.iloc[-2]["close"]
    in_pos = (ctx.position_qty or 0) > 0
    atr_pct = regime.get("atr_pct")
    checks.extend(
        [
            ConditionCheck(
                "atr_vol_cap",
                atr_pct is None or atr_pct <= params.max_atr_pct,
                f"ATR%={atr_pct}",
                "filter",
            ),
            ConditionCheck(
                "entry_squeeze_release",
                not in_pos and was_squeeze and now_expanding and close > prev_close,
                f"squeeze={was_squeeze}, expanding={now_expanding}",
                "entry",
            ),
            ConditionCheck(
                "exit_squeeze_breakdown",
                in_pos and now_expanding and close < prev_close,
                f"close<{prev_close}",
                "exit",
            ),
        ]
    )
    return checks


def audit_supertrend(ctx: StrategyContext, params: SupertrendTrailParams) -> list[ConditionCheck]:
    need = max(params.atr_length, params.ema_filter if params.use_ema_filter else 0) + 10
    checks = [_warmup("warmup_bars", len(ctx.bars) >= need, need, len(ctx.bars))]
    if not checks[0].passed:
        return checks
    df = ctx.bars
    st = ta.supertrend(df["high"], df["low"], df["close"], length=params.atr_length, multiplier=params.multiplier)
    if st is None or st.empty:
        return checks
    dir_col = [c for c in st.columns if c.startswith("SUPERTd")][0]
    d = st[dir_col].iloc[-1]
    pd_prev = st[dir_col].iloc[-2]
    flip_bull = pd_prev < 0 and d > 0
    flip_bear = pd_prev > 0 and d < 0
    close = row["close"] if (row := df.iloc[-1]) is not None else None
    in_pos = (ctx.position_qty or 0) > 0
    ema_ok = True
    if params.use_ema_filter:
        ema = ta.ema(df["close"], length=params.ema_filter)
        ema_ok = ema is not None and pd.notna(ema.iloc[-1]) and close is not None and close >= ema.iloc[-1]
        checks.append(
            ConditionCheck("price_above_ema_filter", ema_ok, f"close={close}", "filter")
        )
    checks.extend(
        [
            ConditionCheck(
                "entry_supertrend_bull_flip",
                not in_pos and flip_bull and ema_ok,
                f"flip_bull={flip_bull}",
                "entry",
            ),
            ConditionCheck(
                "exit_supertrend_bear_flip",
                in_pos and flip_bear,
                f"flip_bear={flip_bear}",
                "exit",
            ),
        ]
    )
    return checks


AUDITORS = {
    "ema_trend": audit_ema_trend,
    "rsi_pullback": audit_rsi_pullback,
    "donchian_breakout": audit_donchian,
    "macd_trend": audit_macd,
    "bb_mean_revert": audit_bb,
    "squeeze_breakout": audit_squeeze,
    "supertrend_trail": audit_supertrend,
}
