from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.db.models import BotHealthStatus, BotStatus, DecisionType, JournalEventType


class BotCreate(BaseModel):
    name: str
    symbol: str = "BTCUSDT"
    timeframe: str = "5m"
    template_id: str = "ema_trend"
    params: dict[str, Any] = Field(default_factory=dict)
    initial_capital: float = 10_000.0


class BotUpdate(BaseModel):
    name: str | None = None
    symbol: str | None = None
    timeframe: str | None = None
    template_id: str | None = None
    params: dict[str, Any] | None = None
    initial_capital: float | None = None


class RunSummary(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None
    starting_equity: float
    template_id: str
    params_snapshot: dict[str, Any]

    model_config = {"from_attributes": True}


class BotOut(BaseModel):
    id: int
    name: str
    status: BotStatus
    symbol: str
    timeframe: str
    template_id: str
    params: dict[str, Any]
    initial_capital: float
    current_run_id: int | None
    created_at: datetime
    equity: float | None = None
    return_pct: float | None = None
    position_qty: float | None = None
    health_status: BotHealthStatus = BotHealthStatus.idle
    last_evaluation_at: datetime | None = None
    last_market_data_at: datetime | None = None
    latest_decision: DecisionType | None = None
    latest_decision_reason: str | None = None
    last_eval_error: str | None = None

    model_config = {"from_attributes": True}


class DecisionLogOut(BaseModel):
    id: int
    bot_id: int
    run_id: int
    evaluated_at: datetime
    candle_open_time: int | None
    symbol_price: float | None
    btc_price: float | None
    market_data_age_sec: float | None
    indicators: dict[str, Any]
    entry_conditions: list[dict[str, Any]]
    exit_conditions: list[dict[str, Any]]
    decision: DecisionType
    reason: str
    rejection_source: str | None
    rejection_detail: str | None

    model_config = {"from_attributes": True}


class StrategyOut(BaseModel):
    id: str
    name: str
    description: str
    category: str
    supported_timeframes: list[str]
    params_schema: dict[str, Any]


class JournalEventOut(BaseModel):
    id: int
    run_id: int
    bot_id: int | None = None
    event_type: JournalEventType
    message: str
    payload: dict[str, Any]
    dedupe_key: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CompareRequest(BaseModel):
    run_ids: list[int]


class SettingsOut(BaseModel):
    fee_bps: float
    slippage_bps: float
    market_connected: bool
    rest_ok: bool
    ws_connected: bool
    last_error: str | None = None
