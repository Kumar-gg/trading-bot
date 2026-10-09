# Always-on deployment (PC off, bots keep running)

The trading **engine** is the FastAPI backend (`uvicorn`). Git stores code; a **host** must run the API 24/7. The React dev server is optional—you can check bots via SSH tunnel or add static UI later.

## Choose a host

| Option | Cost | Always-on | Best for |
|--------|------|-----------|----------|
| **Oracle Cloud Always Free VM** (recommended) | $0 | Yes | Free 24/7 paper bots, full control |
| **Fly.io + volume** | Free tier / card | Yes if machine stays up | Docker-first deploy |
| **Home Raspberry Pi / mini PC** | Hardware once | While device is powered | No cloud account |

This repo supports **systemd + venv** (Oracle/Pi) and **Docker Compose** (any Linux VM).

## Prerequisites

- Git remote (GitHub, GitLab, or Cursor Origin) with this project pushed
- Outbound HTTPS/WSS (Binance data-api / data-stream endpoints)
- Persistent disk for `backend/data/trading_bot.db` (required—do not delete this volume on redeploy)

**State:** Running/paused/stopped status, open positions, and journal are stored in SQLite. API or VM restart resumes **running** bots automatically. Use **Reset** in the UI (or a new DB file) only when you intentionally want a fresh journey.

**Clone URL example:** `git clone https://github.com/Kumar-gg/trading-bot.git /opt/trading-bot`

## 1. Oracle Always Free VM (typical)

1. Create an **Always Free** Ubuntu 22.04/24.04 VM (Ampere ARM is fine).
2. SSH in; install git and Python 3.12:

   ```bash
   sudo apt update && sudo apt install -y git python3.12 python3.12-venv
   ```

3. Clone and install:

   ```bash
   sudo mkdir -p /opt/trading-bot && sudo chown "$USER:$USER" /opt/trading-bot
   git clone YOUR_GIT_URL /opt/trading-bot
   cd /opt/trading-bot/backend
   python3.12 -m venv .venv
   .venv/bin/pip install -e .
   cp ../scripts/deploy/env.example .env
   # edit .env if needed
   mkdir -p data
   ```

4. Install systemd unit:

   ```bash
   sudo cp /opt/trading-bot/scripts/deploy/trading-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now trading-bot
   sudo systemctl status trading-bot
   ```

5. **Firewall:** allow SSH (22). Bind API to `127.0.0.1` in the unit file (default)—use SSH tunnel to access API (see Verify).

6. Start bots (once): from your PC with tunnel, `POST /api/bots/{id}/start` or use Swagger at `/docs`.

## 2. Docker Compose (VM or Pi)

From repo root on the server:

```bash
git clone YOUR_GIT_URL trading-bot && cd trading-bot
cp scripts/deploy/env.example backend/.env
docker compose up -d --build
docker compose logs -f api
```

Data persists in the `trading-bot-data` volume (`/app/data/trading_bot.db` inside the container).

## 3. Fly.io (optional)

See [fly.toml.example](./fly.toml.example). Requires `flyctl`, a volume mounted at `/app/data`, and `TB_DATABASE_URL=sqlite+aiosqlite:///./data/trading_bot.db`.

## Git deploy (updates)

On the server after the first install:

```bash
/opt/trading-bot/scripts/deploy/update-from-git.sh
```

Or manually:

```bash
cd /opt/trading-bot && git pull
cd backend && .venv/bin/pip install -e .
sudo systemctl restart trading-bot
```

## Database backup

Cron example (daily 03:00 UTC):

```bash
chmod +x /opt/trading-bot/scripts/deploy/backup-db.sh
crontab -e
# add:
0 3 * * * /opt/trading-bot/scripts/deploy/backup-db.sh /opt/trading-bot/backend/data /opt/trading-bot/backups
```

Copy `backups/` off the VM with `scp` or cloud object storage.

Restore: stop service, replace `trading_bot.db`, start service.

## Verify (SSH tunnel)

On your **local** machine:

```bash
ssh -L 8000:127.0.0.1:8000 user@YOUR_VM_IP
```

In another terminal:

```bash
cd /opt/trading-bot   # or repo path on Windows
./scripts/deploy/verify-api.sh http://127.0.0.1:8000
```

Windows:

```powershell
.\scripts\deploy\verify-api.ps1 -BaseUrl http://127.0.0.1:8000
```

Checks: `/api/health`, `/api/bots`, `/api/journal`, `/api/decisions`.

## Local production smoke (no UI)

Windows:

```powershell
.\scripts\prod.ps1
```

Linux:

```bash
./scripts/run-api.sh
```

## Security notes

- Prefer **127.0.0.1** binding + SSH tunnel over exposing `:8000` to the internet.
- Do not commit `.env` or `data/*.db`.
- Paper trading only until you explicitly add live keys on the server.
