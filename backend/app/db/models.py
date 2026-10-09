import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BotStatus(str, enum.Enum):
    idle = "idle"
    running = "running"
    paused = "paused"


class BotHealthStatus(str, enum.Enum):
    idle = "idle"
    active = "active"
    stale = "stale"
    error = "error"


class DecisionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    REJECTED = "REJECTED"


class OrderSide(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class OrderType(str, enum.Enum):
    market = "market"
    limit = "limit"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    filled = "filled"
    cancelled = "cancelled"


class JournalEventType(str, enum.Enum):
    signal = "signal"
    risk_rejected = "risk_rejected"
    order_placed = "order_placed"
    fill = "fill"
    stop_hit = "stop_hit"
    take_profit_hit = "take_profit_hit"
    position_exit = "position_exit"
    regime_change = "regime_change"
    strategy_evaluation = "strategy_evaluation"
    decision = "decision"
    equity_snapshot = "equity_snapshot"
    bot_started = "bot_started"
    bot_paused = "bot_paused"
    bot_stopped = "bot_stopped"
    run_reset = "run_reset"
    error = "error"


class PositionLeg(str, enum.Enum):
    entry = "entry"
    exit = "exit"


class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[BotStatus] = mapped_column(
        Enum(BotStatus), default=BotStatus.idle, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), default="BTCUSDT", nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), default="5m", nullable=False)
    template_id: Mapped[str] = mapped_column(String(64), default="ema_trend", nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    initial_capital: Mapped[float] = mapped_column(Float, default=10_000.0)
    current_run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("runs.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    health_status: Mapped[BotHealthStatus] = mapped_column(
        Enum(BotHealthStatus), default=BotHealthStatus.idle, nullable=False
    )
    last_evaluation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_market_data_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    latest_decision: Mapped[DecisionType | None] = mapped_column(
        Enum(DecisionType), nullable=True
    )
    latest_decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_eval_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    runs: Mapped[list["Run"]] = relationship(
        "Run",
        back_populates="bot",
        foreign_keys="Run.bot_id",
    )
    current_run: Mapped["Run | None"] = relationship(
        "Run",
        foreign_keys=[current_run_id],
        post_update=True,
    )


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey("bots.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    starting_equity: Mapped[float] = mapped_column(Float, nullable=False)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    params_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    position_qty: Mapped[float] = mapped_column(Float, default=0.0)
    position_avg_entry: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    peak_equity: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_bar_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cooldown_until_bar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_regime_signature: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active_trade_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    bot: Mapped["Bot"] = relationship(
        "Bot",
        back_populates="runs",
        foreign_keys=[bot_id],
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="run")
    journal_events: Mapped[list["JournalEvent"]] = relationship(
        "JournalEvent", back_populates="run"
    )
    equity_snapshots: Mapped[list["EquitySnapshot"]] = relationship(
        "EquitySnapshot", back_populates="run"
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"), nullable=False)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    limit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["Run"] = relationship("Run", back_populates="orders")
    fills: Mapped[list["Fill"]] = relationship("Fill", back_populates="order")


class Fill(Base):
    __tablename__ = "fills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    slippage_bps: Mapped[float] = mapped_column(Float, default=0.0)
    filled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    candle_open_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    regime_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    position_leg: Mapped[PositionLeg | None] = mapped_column(Enum(PositionLeg), nullable=True)
    trade_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    order: Mapped["Order"] = relationship("Order", back_populates="fills")


class JournalEvent(Base):
    __tablename__ = "journal_events"
    __table_args__ = (
        UniqueConstraint("run_id", "dedupe_key", name="uq_journal_dedupe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"), nullable=False, index=True)
    bot_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("bots.id"), nullable=True, index=True)
    event_type: Mapped[JournalEventType] = mapped_column(Enum(JournalEventType), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    run: Mapped["Run"] = relationship("Run", back_populates="journal_events")


class EquitySnapshot(Base):
    __tablename__ = "equity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"), nullable=False)
    equity: Mapped[float] = mapped_column(Float, nullable=False)
    mark_price: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["Run"] = relationship("Run", back_populates="equity_snapshots")


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey("bots.id"), index=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"), index=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    candle_open_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symbol_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    btc_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_data_age_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    indicators: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    entry_conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    exit_conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    decision: Mapped[DecisionType] = mapped_column(Enum(DecisionType), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    rejection_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rejection_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class CandleCache(Base):
    __tablename__ = "candle_cache"
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "open_time", name="uq_candle"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    open_time: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    closed: Mapped[bool] = mapped_column(default=True)
