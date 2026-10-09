#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"

check() {
  local path="$1"
  local code
  code="$(curl -sf -o /tmp/tb_verify.json -w "%{http_code}" "$BASE$path")"
  if [[ "$code" != "200" ]]; then
    echo "FAIL $path HTTP $code" >&2
    exit 1
  fi
  echo "OK   $path"
}

check "/api/health"
check "/api/bots"
check "/api/strategies"
check "/api/journal?limit=5"
check "/api/decisions?limit=5"

echo "All checks passed against $BASE"
