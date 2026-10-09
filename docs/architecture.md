# Architecture

Local single-user stack:

- **Frontend** (`frontend/`): Vite + React + TanStack Query, proxied to the API.
- **Backend** (`backend/app/`): FastAPI, async SQLAlchemy + SQLite (WAL).
- **MarketDataService**: shared Binance Spot kline WebSocket + REST backfill.
- **BotEngine**: evaluates strategies on **closed** candles for running bots.
- **PaperBroker**: simulated fills, fees, slippage, bracket SL/TP.
- **StrategyRegistry**: Pydantic parameter models → JSON Schema for UI forms.

Bot lifecycle: `idle` → `running` ↔ `paused` → `stop` archives run. **Reset journey** closes the current run and opens a new one with fresh capital.
