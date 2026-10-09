from datetime import datetime, timedelta, timezone

import pytest

from app.db.models import Bot, BotHealthStatus, BotStatus
from app.services.health import compute_health, expected_eval_interval_sec


@pytest.mark.unit
def test_expected_interval_5m():
    assert expected_eval_interval_sec("5m") == 450.0


@pytest.mark.unit
def test_running_bot_stale_without_eval():
    bot = Bot(name="x", status=BotStatus.running, timeframe="5m")
    assert compute_health(bot, market_age_sec=10) == BotHealthStatus.stale


@pytest.mark.unit
def test_running_bot_active_after_recent_eval():
    bot = Bot(name="x", status=BotStatus.running, timeframe="5m")
    bot.last_evaluation_at = datetime.now(timezone.utc)
    assert compute_health(bot, market_age_sec=5) == BotHealthStatus.active


@pytest.mark.unit
def test_running_bot_stale_old_eval():
    bot = Bot(name="x", status=BotStatus.running, timeframe="5m")
    bot.last_evaluation_at = datetime.now(timezone.utc) - timedelta(hours=2)
    assert compute_health(bot, market_age_sec=5) == BotHealthStatus.stale


@pytest.mark.unit
def test_idle_bot_health():
    bot = Bot(name="x", status=BotStatus.idle, timeframe="5m")
    assert compute_health(bot, market_age_sec=None) == BotHealthStatus.idle


@pytest.mark.unit
def test_running_bot_naive_last_eval_from_sqlite():
    """SQLite returns naive UTC; health checks must not crash."""
    bot = Bot(name="x", status=BotStatus.running, timeframe="5m")
    bot.last_evaluation_at = datetime.utcnow()
    assert compute_health(bot, market_age_sec=5) == BotHealthStatus.active
