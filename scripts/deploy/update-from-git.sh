#!/usr/bin/env bash
# Pull latest code and restart the systemd service (adjust paths if needed).
set -euo pipefail
INSTALL_ROOT="${INSTALL_ROOT:-/opt/trading-bot}"
SERVICE="${SERVICE:-trading-bot}"

cd "$INSTALL_ROOT"
git pull --ff-only
cd backend
if [[ -d .venv ]]; then
  .venv/bin/pip install -e .
else
  python3 -m venv .venv
  .venv/bin/pip install -e .
fi

if systemctl is-active --quiet "$SERVICE" 2>/dev/null; then
  sudo systemctl restart "$SERVICE"
  echo "Restarted $SERVICE"
elif command -v docker >/dev/null && [[ -f "$INSTALL_ROOT/docker-compose.yml" ]]; then
  cd "$INSTALL_ROOT"
  docker compose up -d --build
  echo "Docker compose rebuilt"
else
  echo "Install complete. Start manually: systemctl start $SERVICE or docker compose up -d"
fi
