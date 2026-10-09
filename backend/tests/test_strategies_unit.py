import pandas as pd
import pytest

from app.strategies.indicators import classify_regime_label, compute_regime, enrich_bars
from app.strategies.registry import strategy_registry


@pytest.mark.unit
def test_registry_lists_all_templates():
    metas = strategy_registry.list_metadata()
    assert len(metas) == 7
    schema = strategy_registry.params_schema("bb_mean_revert")
    assert "properties" in schema


@pytest.mark.unit
def test_ema_trend_params_validation():
    with pytest.raises(Exception):
        strategy_registry.parse_params("ema_trend", {"ema_fast": 999})


@pytest.mark.unit
def test_classify_regime_labels():
    assert classify_regime_label(25, 1.0) == "trend"
    assert classify_regime_label(15, 1.0) == "range"
    assert classify_regime_label(25, 4.0) == "high_vol"


@pytest.mark.unit
def test_enrich_bars_and_regime():
    n = 80
    df = pd.DataFrame(
        {
            "open_time": range(n),
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.0 + i * 0.01 for i in range(n)],
            "volume": [1000.0] * n,
        }
    )
    enriched = enrich_bars(df)
    assert "adx" in enriched.columns
    regime = compute_regime(enriched.iloc[-1])
    assert regime["label"] in ("trend", "range", "high_vol", "neutral")
