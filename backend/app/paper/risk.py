from dataclasses import dataclass

from app.strategies.types import Signal, SignalAction


@dataclass
class RiskConfig:
    max_position_pct: float = 100.0
    max_open_positions: int = 1
    daily_loss_limit_pct: float = 5.0
    max_drawdown_pct: float = 15.0
    cooldown_bars: int = 0


@dataclass
class RiskDecision:
    allowed: bool
    reason: str = ""
    qty: float = 0.0


class RiskManager:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def evaluate_entry(
        self,
        signal: Signal,
        equity: float,
        mark_price: float,
        position_qty: float,
        current_bar_index: int,
        cooldown_until_bar: int | None,
        starting_equity: float,
        peak_equity: float,
    ) -> RiskDecision:
        if signal.action not in (SignalAction.buy,):
            return RiskDecision(True, qty=0)

        if position_qty > 0:
            return RiskDecision(False, "Already in position")

        if cooldown_until_bar is not None and current_bar_index < cooldown_until_bar:
            return RiskDecision(False, "Cooldown active")

        dd = 0.0
        if peak_equity > 0:
            dd = (peak_equity - equity) / peak_equity * 100
        if dd >= self.config.max_drawdown_pct:
            return RiskDecision(False, f"Max drawdown reached ({dd:.1f}%)")

        day_loss = (starting_equity - equity) / starting_equity * 100
        if day_loss >= self.config.daily_loss_limit_pct:
            return RiskDecision(False, "Daily loss limit reached")

        position_pct = signal.metadata.get("position_pct", self.config.max_position_pct)
        position_pct = min(position_pct, self.config.max_position_pct)
        notional = equity * (position_pct / 100.0)
        if mark_price <= 0:
            return RiskDecision(False, "Invalid mark price")
        qty = notional / mark_price
        if qty <= 0:
            return RiskDecision(False, "Position size too small")
        return RiskDecision(True, qty=qty)

    def evaluate_exit(self, signal: Signal, position_qty: float) -> RiskDecision:
        if signal.action in (SignalAction.sell, SignalAction.close):
            if position_qty <= 0:
                return RiskDecision(False, "No position to close")
            return RiskDecision(True, qty=position_qty)
        return RiskDecision(True)
