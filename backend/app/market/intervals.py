TIMEFRAME_TO_BINANCE = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
}

TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
}


def binance_interval(timeframe: str) -> str:
    if timeframe not in TIMEFRAME_TO_BINANCE:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return TIMEFRAME_TO_BINANCE[timeframe]
