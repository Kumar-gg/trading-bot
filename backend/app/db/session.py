from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


_BOT_COLUMN_MIGRATIONS: list[tuple[str, str]] = [
    ("health_status", "VARCHAR(16) DEFAULT 'idle'"),
    ("last_evaluation_at", "DATETIME"),
    ("last_market_data_at", "DATETIME"),
    ("latest_decision", "VARCHAR(16)"),
    ("latest_decision_reason", "TEXT"),
    ("last_eval_error", "TEXT"),
]


_RUN_COLUMN_MIGRATIONS: list[tuple[str, str]] = [
    ("last_regime_signature", "VARCHAR(64)"),
    ("active_trade_group_id", "VARCHAR(36)"),
]

_JOURNAL_COLUMN_MIGRATIONS: list[tuple[str, str]] = [
    ("dedupe_key", "VARCHAR(128)"),
    ("bot_id", "INTEGER"),
]

_FILL_COLUMN_MIGRATIONS: list[tuple[str, str]] = [
    ("candle_open_time", "INTEGER"),
    ("regime_snapshot", "JSON"),
    ("position_leg", "VARCHAR(16)"),
    ("trade_group_id", "VARCHAR(36)"),
]


async def _add_columns(conn, table: str, migrations: list[tuple[str, str]]) -> None:
    result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
    existing = {row[1] for row in result.fetchall()}
    for col, typedef in migrations:
        if col not in existing:
            await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")


async def _migrate_legacy_schema(conn) -> None:
    await _add_columns(conn, "bots", _BOT_COLUMN_MIGRATIONS)
    await _add_columns(conn, "runs", _RUN_COLUMN_MIGRATIONS)
    await _add_columns(conn, "journal_events", _JOURNAL_COLUMN_MIGRATIONS)
    await _add_columns(conn, "fills", _FILL_COLUMN_MIGRATIONS)
    await conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_journal_dedupe "
        "ON journal_events (run_id, dedupe_key) WHERE dedupe_key IS NOT NULL"
    )


async def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_legacy_schema(conn)
