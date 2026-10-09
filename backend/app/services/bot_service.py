from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Bot, BotHealthStatus, BotStatus, EquitySnapshot, JournalEventType, Run
from app.services.journal import try_log_journal
from app.engine.bot_worker import BotEngine
from app.engine.events import StreamEvent, event_bus
from app.paper.broker import PaperBroker
from app.strategies.registry import strategy_registry


async def create_run(session: AsyncSession, bot: Bot) -> Run:
    run = Run(
        bot_id=bot.id,
        starting_equity=bot.initial_capital,
        template_id=bot.template_id,
        params_snapshot=dict(bot.params),
        cash=bot.initial_capital,
        peak_equity=bot.initial_capital,
    )
    session.add(run)
    await session.flush()
    bot.current_run_id = run.id
    return run


async def list_bots(session: AsyncSession) -> list[Bot]:
    result = await session.execute(select(Bot).order_by(Bot.id))
    return list(result.scalars().all())


async def get_bot(session: AsyncSession, bot_id: int) -> Bot | None:
    return await session.get(Bot, bot_id)


async def create_bot(session: AsyncSession, data: dict) -> Bot:
    template_id = data.get("template_id", "ema_trend")
    strategy_registry.parse_params(template_id, data.get("params") or {})
    bot = Bot(
        name=data["name"],
        symbol=data.get("symbol", "BTCUSDT").upper(),
        timeframe=data.get("timeframe", "5m"),
        template_id=template_id,
        params=data.get("params") or {},
        initial_capital=float(data.get("initial_capital", 10_000)),
        status=BotStatus.idle,
    )
    session.add(bot)
    await session.flush()
    await create_run(session, bot)
    await session.commit()
    await session.refresh(bot)
    return bot


async def update_bot(session: AsyncSession, bot: Bot, data: dict) -> Bot:
    if bot.status == BotStatus.running:
        raise ValueError("Pause bot before editing")
    run = await session.get(Run, bot.current_run_id) if bot.current_run_id else None
    if run and run.position_qty > 0:
        raise ValueError("Close positions before editing (reset or stop)")

    if "name" in data:
        bot.name = data["name"]
    if "symbol" in data:
        bot.symbol = data["symbol"].upper()
    if "timeframe" in data:
        bot.timeframe = data["timeframe"]
    if "template_id" in data:
        bot.template_id = data["template_id"]
    if "params" in data:
        strategy_registry.parse_params(bot.template_id, data["params"])
        bot.params = data["params"]
    if "initial_capital" in data:
        bot.initial_capital = float(data["initial_capital"])
    await session.commit()
    await session.refresh(bot)
    return bot


async def start_bot(session: AsyncSession, bot: Bot, engine: BotEngine) -> Bot:
    if bot.status == BotStatus.running:
        return bot
    if not bot.current_run_id:
        await create_run(session, bot)
    run = await session.get(Run, bot.current_run_id)
    if run and run.ended_at:
        run.ended_at = None
    bot.status = BotStatus.running
    bot.health_status = BotHealthStatus.stale
    bot.last_eval_error = None
    if run:
        await try_log_journal(
            session,
            run,
            JournalEventType.bot_started,
            f"Bot started ({bot.symbol} {bot.timeframe})",
            {"symbol": bot.symbol, "timeframe": bot.timeframe, "template_id": bot.template_id},
            dedupe_key=f"lifecycle:started:{run.id}",
            bot_id=bot.id,
        )
    await session.commit()
    await engine.sync_subscriptions(session)
    await event_bus.publish(StreamEvent(type="bot_update", payload={"bot_id": bot.id}))
    return bot


async def pause_bot(session: AsyncSession, bot: Bot, engine: BotEngine) -> Bot:
    bot.status = BotStatus.paused
    bot.health_status = BotHealthStatus.idle
    await session.commit()
    await engine.sync_subscriptions(session)
    return bot


async def stop_bot(session: AsyncSession, bot: Bot, engine: BotEngine) -> Bot:
    """Halt trading but keep the same run, positions, and journal (only Reset archives)."""
    bot.status = BotStatus.idle
    bot.health_status = BotHealthStatus.idle
    if bot.current_run_id:
        run = await session.get(Run, bot.current_run_id)
        if run:
            await try_log_journal(
                session,
                run,
                JournalEventType.bot_stopped,
                "Bot stopped (journey preserved)",
                dedupe_key=f"lifecycle:stopped:{run.id}:{int(datetime.now(timezone.utc).timestamp())}",
                bot_id=bot.id,
            )
    await session.commit()
    await engine.sync_subscriptions(session)
    return bot


async def reset_bot(session: AsyncSession, bot: Bot, engine: BotEngine) -> Bot:
    was_running = bot.status == BotStatus.running
    bot.status = BotStatus.idle
    if bot.current_run_id:
        run = await session.get(Run, bot.current_run_id)
        if run and not run.ended_at:
            run.ended_at = datetime.now(timezone.utc)
    new_run = await create_run(session, bot)
    await try_log_journal(
        session,
        new_run,
        JournalEventType.run_reset,
        "New trading journey started",
        {"previous_run_archived": True},
        dedupe_key=f"lifecycle:reset:{new_run.id}",
        bot_id=bot.id,
    )
    await session.commit()
    if was_running:
        bot.status = BotStatus.running
        await session.commit()
    await engine.sync_subscriptions(session)
    await session.refresh(bot)
    return bot


async def snapshot_equity_for_runs(session: AsyncSession, engine_market) -> None:
    broker = PaperBroker()
    result = await session.execute(select(Bot).where(Bot.status == BotStatus.running))
    for bot in result.scalars():
        if not bot.current_run_id:
            continue
        run = await session.get(Run, bot.current_run_id)
        if not run:
            continue
        mark = engine_market.get_mark_price(bot.symbol) or 0.0
        if mark <= 0:
            continue
        eq = broker.mark_equity(run, mark)
        session.add(EquitySnapshot(run_id=run.id, equity=eq, mark_price=mark))
    await session.commit()
