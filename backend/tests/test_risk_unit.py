import pytest

from app.paper.risk import RiskManager
from app.strategies.types import Signal, SignalAction


@pytest.mark.unit
def test_risk_rejects_second_position():
    rm = RiskManager()
    sig = Signal(action=SignalAction.buy, metadata={"position_pct": 25})
    d = rm.evaluate_entry(sig, 10_000, 100, 1.0, 0, None, 10_000, 10_000)
    assert not d.allowed
    assert "Already" in d.reason


@pytest.mark.unit
def test_risk_allows_entry_when_flat():
    rm = RiskManager()
    sig = Signal(action=SignalAction.buy, metadata={"position_pct": 25})
    d = rm.evaluate_entry(sig, 10_000, 100, 0, 0, None, 10_000, 10_000)
    assert d.allowed
    assert d.qty > 0
