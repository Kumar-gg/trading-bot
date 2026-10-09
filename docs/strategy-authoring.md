# Strategy authoring

Add a module under `backend/app/strategies/templates/`:

1. Define a **Pydantic** params class (bounds become JSON Schema for the UI).
2. Implement `StrategyTemplate` with `metadata` (include `category`: `trend`, `mean_reversion`, `breakout`, or `volatility`), `params_model`, `warmup_bars`, and `on_bar(ctx, params)`.
3. Register the instance in `templates/__init__.py` → `ALL_TEMPLATES`.

`StrategyContext` provides OHLCV (`bars` DataFrame with indicator columns from `enrich_bars`), position, equity, and mark price.

Return `Signal` with `buy`, `close`, optional `stop_loss_pct` / `take_profit_pct`, and `metadata` (include `position_pct` for sizing).

Strategies must only act on **closed** bars (enforced by the engine).
