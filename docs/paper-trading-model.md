# Paper trading model

## Fills

- **Market orders** fill at the reference price (candle close for bar strategies, last kline close for marks) adjusted by **slippage bps** (default 5).
- **Fees** apply as bps on notional (default 10 bps per side).

## Positions

- Average entry for adds; realized PnL on sells uses average entry.
- Equity = cash + position_qty × mark_price.

## Brackets

- Optional stop-loss and take-profit percentages from strategy signals set `stop_loss_price` / `take_profit_price`.
- On each closed bar, if high/low crosses a bracket, a market sell is simulated.

## Risk

- Position size from strategy `position_pct` capped by risk config.
- Max drawdown and daily loss limits can auto-pause the bot.

## Limitations (honest paper)

- No order-book queue, partial fills, or latency model.
- Same bar may trigger both signal and bracket; stops are evaluated before new signals on a bar.
