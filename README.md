# Trading Bot

Multi-bot **paper trading** web app for live **Binance Spot** crypto prices.

## Features

- Multiple bots with isolated paper accounts
- Strategy templates with UI-tunable parameters (EMA trend, RSI pullback, Donchian breakout)
- Start / pause / stop / reset journey (archived runs for comparison)
- Per-run trade journal + CSV export
- Dashboard and compare view with metrics and insights

## Quick start (Windows)

```powershell
cd "F:\Trading\Trading Bot\scripts"
.\dev.ps1
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Manual start

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

cd frontend
npm run dev
```

## Tests

Run the full pipeline (backend smoke + full pytest, frontend build, unit, E2E):

```powershell
cd "F:\Trading\Trading Bot\scripts"
.\test-all.ps1
```

Individual suites:

```powershell
cd backend
.\.venv\Scripts\pytest -m smoke
.\.venv\Scripts\pytest

cd frontend
npm run test:unit
npm run test:e2e
```

## Docs

- [architecture.md](docs/architecture.md)
- [paper-trading-model.md](docs/paper-trading-model.md)
- [strategy-authoring.md](docs/strategy-authoring.md)

Database file: `backend/data/trading_bot.db` (backup this file to preserve history).

**State persistence:** Bot status, positions, journal, and runs live in SQLite. Closing the browser or restarting the API does not reset them. **Stop** halts trading but keeps the same run; only **Reset** starts a new journey. On the VM, keep the same `data/` volume so reboots continue where you left off.

## Always-on hosting (PC off)

To keep paper bots evaluating 24/7, run the **backend** on a cloud VM or home Pi—not on a sleeping PC. Git deploys code; a host runs the process.

See **[scripts/deploy/README.md](scripts/deploy/README.md)** for Oracle Free VM, Docker Compose, git pull updates, backups, and SSH tunnel verification.

Quick local production API (no Vite):

```powershell
.\scripts\prod.ps1
```
