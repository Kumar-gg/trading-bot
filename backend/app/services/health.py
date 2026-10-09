from datetime import datetime

from app.db.models import Bot, BotHealthStatus, BotStatus
from app.market.intervals import TIMEFRAME_MS
from app.util.datetime_util import ensure_utc, utcnow


def expected_eval_interval_sec(timeframe: str) -> float:
    ms = TIMEFRAME_MS.get(timeframe, 300_000)
    return ms / 1000.0 * 1.5  # allow 50% slack after candle close


def compute_health(
    bot: Bot,
    *,
    market_age_sec: float | None,
    now: datetime | None = None,
) -> BotHealthStatus:
    now = ensure_utc(now) or utcnow()
    if bot.status != BotStatus.running:
        return BotHealthStatus.idle

    if bot.last_eval_error:
        return BotHealthStatus.error

    if bot.last_evaluation_at is None:
        return BotHealthStatus.stale

    last_eval = ensure_utc(bot.last_evaluation_at)
    if last_eval is None:
        return BotHealthStatus.stale
    eval_age = (now - last_eval).total_seconds()
    max_eval = expected_eval_interval_sec(bot.timeframe) + 120
    if eval_age > max_eval:
        return BotHealthStatus.stale

    if market_age_sec is not None and market_age_sec > max_eval:
        return BotHealthStatus.stale

    return BotHealthStatus.active


def refresh_bot_health(
    bot: Bot,
    market_age_sec: float | None,
    now: datetime | None = None,
) -> None:
    bot.health_status = compute_health(bot, market_age_sec=market_age_sec, now=now)
