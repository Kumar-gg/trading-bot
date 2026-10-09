from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd
from pydantic import BaseModel


class SignalAction(str, Enum):
    buy = "buy"
    sell = "sell"
    close = "close"
    hold = "hold"


@dataclass
class Signal:
    action: SignalAction
    reason: str = ""
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyContext:
    symbol: str
    timeframe: str
    bars: pd.DataFrame
    position_qty: float
    position_avg_entry: float | None
    equity: float
    cash: float
    mark_price: float
    regime: dict[str, Any] = field(default_factory=dict)


StrategyCategory = str  # trend | mean_reversion | breakout | volatility


class StrategyMetadata(BaseModel):
    id: str
    name: str
    description: str
    category: StrategyCategory
    supported_timeframes: list[str]


class StrategyTemplate:
    metadata: StrategyMetadata
    params_model: type[BaseModel]

    def warmup_bars(self, params: BaseModel) -> int:
        return 50

    def on_bar(self, ctx: StrategyContext, params: BaseModel) -> Signal | None:
        raise NotImplementedError
