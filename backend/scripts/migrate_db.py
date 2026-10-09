"""Add decision-log columns to an existing SQLite DB (run once if upgrading)."""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "trading_bot.db"

ALTERS = [
    "ALTER TABLE bots ADD COLUMN health_status VARCHAR(16) DEFAULT 'idle'",
    "ALTER TABLE bots ADD COLUMN last_evaluation_at DATETIME",
    "ALTER TABLE bots ADD COLUMN last_market_data_at DATETIME",
    "ALTER TABLE bots ADD COLUMN latest_decision VARCHAR(16)",
    "ALTER TABLE bots ADD COLUMN latest_decision_reason TEXT",
    "ALTER TABLE bots ADD COLUMN last_eval_error TEXT",
]


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DB
    if not path.exists():
        print(f"No database at {path}")
        return 0
    conn = sqlite3.connect(path)
    for sql in ALTERS:
        try:
            conn.execute(sql)
            print("OK:", sql[:60])
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("skip:", sql[:40])
            else:
                raise
    conn.commit()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS decision_logs ("
        "id INTEGER PRIMARY KEY, bot_id INTEGER, run_id INTEGER, "
        "evaluated_at DATETIME, candle_open_time INTEGER, symbol_price FLOAT, "
        "btc_price FLOAT, market_data_age_sec FLOAT, indicators JSON, "
        "entry_conditions JSON, exit_conditions JSON, decision VARCHAR(16), "
        "reason TEXT, rejection_source VARCHAR(64), rejection_detail TEXT)"
    )
    conn.commit()
    conn.close()
    print("Migration done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
