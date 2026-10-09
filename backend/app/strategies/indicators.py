import pandas as pd
import pandas_ta as ta


def enrich_bars(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty or len(out) < 3:
        return out
    out["ema_fast"] = ta.ema(out["close"], length=12)
    out["ema_slow"] = ta.ema(out["close"], length=26)
    out["rsi"] = ta.rsi(out["close"], length=14)
    adx = ta.adx(out["high"], out["low"], out["close"], length=14)
    if adx is not None and not adx.empty:
        adx_col = [c for c in adx.columns if c.upper().startswith("ADX")]
        out["adx"] = adx[adx_col[0]] if adx_col else float("nan")
    else:
        out["adx"] = float("nan")
    out["atr"] = ta.atr(out["high"], out["low"], out["close"], length=14)
    out["donchian_high"] = out["high"].rolling(20).max()
    out["donchian_low"] = out["low"].rolling(20).min()
    return out


def compute_regime(row: pd.Series) -> dict:
    ema_fast = row.get("ema_fast")
    ema_slow = row.get("ema_slow")
    adx = row.get("adx")
    atr = row.get("atr")
    close = row.get("close")
    trend = "neutral"
    if pd.notna(ema_fast) and pd.notna(ema_slow):
        if ema_fast > ema_slow:
            trend = "bull"
        elif ema_fast < ema_slow:
            trend = "bear"
    atr_pct = None
    if pd.notna(atr) and pd.notna(close) and close:
        atr_pct = float(atr / close * 100)
    label = classify_regime_label(adx, atr_pct)
    return {
        "trend": trend,
        "adx": float(adx) if pd.notna(adx) else None,
        "atr_pct": atr_pct,
        "close": float(close) if pd.notna(close) else None,
        "label": label,
    }


def classify_regime_label(
    adx: float | None, atr_pct: float | None, *, adx_trend: float = 22.0, adx_range: float = 18.0, high_vol_atr: float = 3.0
) -> str:
    if atr_pct is not None and atr_pct >= high_vol_atr:
        return "high_vol"
    if adx is not None:
        if adx >= adx_trend:
            return "trend"
        if adx <= adx_range:
            return "range"
    return "neutral"
