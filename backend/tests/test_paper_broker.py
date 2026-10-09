from app.db.models import Run
from app.paper.broker import FillResult, PaperBroker, OrderSide


def test_market_buy_and_sell_pnl():
    broker = PaperBroker(fee_bps=10, slippage_bps=0)
    run = Run(
        bot_id=1,
        starting_equity=10_000,
        template_id="ema_trend",
        cash=10_000,
        peak_equity=10_000,
    )
    buy = broker.market_fill(OrderSide.buy, 1.0, 100.0)
    broker.apply_fill_to_run(run, OrderSide.buy, buy)
    assert run.position_qty == 1.0
    assert run.position_avg_entry == buy.price

    sell = broker.market_fill(OrderSide.sell, 1.0, 110.0)
    broker.apply_fill_to_run(run, OrderSide.sell, sell)
    assert run.position_qty == 0
    assert run.realized_pnl > 0


def test_stop_loss_detection():
    broker = PaperBroker()
    run = Run(
        bot_id=1,
        starting_equity=10_000,
        template_id="ema_trend",
        cash=5_000,
        peak_equity=10_000,
        position_qty=1.0,
        position_avg_entry=100.0,
        stop_loss_price=95.0,
    )
    assert broker.check_stops(run, 101, 94.0) == OrderSide.sell
    assert broker.check_stops(run, 101, 96.0) is None


def test_bracket():
    broker = PaperBroker()
    run = Run(
        bot_id=1,
        starting_equity=10_000,
        template_id="ema_trend",
        cash=10_000,
        peak_equity=10_000,
    )
    broker.set_bracket(run, 100.0, 2.0, 4.0)
    assert run.stop_loss_price == 98.0
    assert run.take_profit_price == 104.0
