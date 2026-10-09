from dataclasses import dataclass

from app.config import settings
from app.db.models import OrderSide, OrderStatus, OrderType, Run


@dataclass
class FillResult:
    price: float
    qty: float
    fee: float
    slippage_bps: float


class PaperBroker:
    def __init__(
        self,
        fee_bps: float | None = None,
        slippage_bps: float | None = None,
    ) -> None:
        self.fee_bps = fee_bps if fee_bps is not None else settings.default_fee_bps
        self.slippage_bps = (
            slippage_bps if slippage_bps is not None else settings.default_slippage_bps
        )

    def apply_slippage(self, price: float, side: OrderSide) -> tuple[float, float]:
        slip = self.slippage_bps / 10_000.0
        if side == OrderSide.buy:
            fill = price * (1 + slip)
        else:
            fill = price * (1 - slip)
        return fill, self.slippage_bps

    def compute_fee(self, notional: float) -> float:
        return notional * (self.fee_bps / 10_000.0)

    def market_fill(self, side: OrderSide, qty: float, mark_price: float) -> FillResult:
        price, slip_bps = self.apply_slippage(mark_price, side)
        notional = price * qty
        fee = self.compute_fee(notional)
        return FillResult(price=price, qty=qty, fee=fee, slippage_bps=slip_bps)

    @staticmethod
    def mark_equity(run: Run, mark_price: float) -> float:
        pos_value = (run.position_qty or 0.0) * mark_price
        return run.cash + pos_value

    @staticmethod
    def unrealized_pnl(run: Run, mark_price: float) -> float:
        if (run.position_qty or 0.0) <= 0 or not run.position_avg_entry:
            return 0.0
        return (mark_price - run.position_avg_entry) * run.position_qty

    def apply_fill_to_run(self, run: Run, side: OrderSide, fill: FillResult) -> None:
        notional = fill.price * fill.qty
        if side == OrderSide.buy:
            total_cost = notional + fill.fee
            if total_cost > run.cash:
                affordable = max(run.cash - fill.fee, 0) / fill.price
                fill.qty = affordable
                notional = fill.price * fill.qty
                total_cost = notional + fill.fee
            prev_qty = run.position_qty or 0.0
            new_qty = prev_qty + fill.qty
            if new_qty > 0:
                if prev_qty > 0 and run.position_avg_entry:
                    run.position_avg_entry = (
                        run.position_avg_entry * prev_qty + fill.price * fill.qty
                    ) / new_qty
                else:
                    run.position_avg_entry = fill.price
            run.position_qty = new_qty
            run.cash -= total_cost
        else:
            proceeds = notional - fill.fee
            if run.position_avg_entry:
                run.realized_pnl = (run.realized_pnl or 0.0) + (
                    fill.price - run.position_avg_entry
                ) * fill.qty
            run.cash += proceeds
            run.position_qty = max((run.position_qty or 0.0) - fill.qty, 0.0)
            if run.position_qty == 0:
                run.position_avg_entry = None
                run.stop_loss_price = None
                run.take_profit_price = None

    def check_stops(self, run: Run, bar_high: float, bar_low: float) -> OrderSide | None:
        if (run.position_qty or 0.0) <= 0:
            return None
        if run.stop_loss_price is not None and bar_low <= run.stop_loss_price:
            return OrderSide.sell
        if run.take_profit_price is not None and bar_high >= run.take_profit_price:
            return OrderSide.sell
        return None

    @staticmethod
    def set_bracket(run: Run, entry_price: float, stop_loss_pct: float | None, take_profit_pct: float | None) -> None:
        if stop_loss_pct:
            run.stop_loss_price = entry_price * (1 - stop_loss_pct / 100.0)
        if take_profit_pct:
            run.take_profit_price = entry_price * (1 + take_profit_pct / 100.0)


def order_side_for_signal_action(action: str) -> OrderSide:
    if action in ("buy",):
        return OrderSide.buy
    return OrderSide.sell


def pending_order_types() -> OrderType:
    return OrderType.market


def filled_status() -> OrderStatus:
    return OrderStatus.filled
