#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
cd "$BACKEND"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -e .
fi

mkdir -p data
export TB_DATABASE_URL="${TB_DATABASE_URL:-sqlite+aiosqlite:///./data/trading_bot.db}"

exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
