from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TB_")

    database_url: str = "sqlite+aiosqlite:///./data/trading_bot.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v  # type: ignore[return-value]
    default_fee_bps: float = 10.0
    default_slippage_bps: float = 5.0
    # Public market-data endpoints (works when api.binance.com is blocked, e.g. some regions)
    binance_rest: str = "https://data-api.binance.vision"
    binance_ws: str = "wss://data-stream.binance.vision/ws"
    equity_snapshot_interval_sec: int = 60

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("sqlite+aiosqlite", "sqlite")

    @property
    def data_dir(self) -> Path:
        return Path("./data")


settings = Settings()
