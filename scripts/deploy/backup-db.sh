#!/usr/bin/env bash
# Safe SQLite backup using .backup (handles WAL). Usage:
#   backup-db.sh /path/to/data/dir /path/to/backup/dir
set -euo pipefail

DATA_DIR="${1:-./data}"
BACKUP_DIR="${2:-./backups}"
DB="$DATA_DIR/trading_bot.db"

if [[ ! -f "$DB" ]]; then
  echo "No database at $DB" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/trading_bot_${STAMP}.db"

if command -v sqlite3 >/dev/null; then
  sqlite3 "$DB" ".backup '$OUT'"
else
  cp "$DB" "$OUT"
  [[ -f "$DATA_DIR/trading_bot.db-wal" ]] && cp "$DATA_DIR/trading_bot.db-wal" "$OUT-wal" || true
fi

# Keep last 14 backups
ls -1t "$BACKUP_DIR"/trading_bot_*.db 2>/dev/null | tail -n +15 | xargs -r rm -f
echo "Backup written: $OUT"
