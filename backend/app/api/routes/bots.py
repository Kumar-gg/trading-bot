from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import BotCreate, BotOut, BotUpdate, JournalEventOut, RunSummary
from app.db.models import Bot, Run
from app.db.session import get_db
from app.paper.broker import PaperBroker
from app.services import bot_service
from app.services.health import refresh_bot_health

router = APIRouter(prefix="/bots", tags=["bots"])


def _engine(request: Request):
    return request.app.state.engine


async def _bot_to_out(session: AsyncSession, bot: Bot, market) -> BotOut:
    age = market.market_data_age_sec(bot.symbol, bot.timeframe)
    refresh_bot_health(bot, age)
    out = BotOut.model_validate(bot)
    if bot.current_run_id:
        run = await session.get(Run, bot.current_run_id)
        if run:
            mark = market.get_mark_price(bot.symbol) or 0.0
            if mark > 0:
                eq = PaperBroker().mark_equity(run, mark)
            else:
                eq = run.cash + (run.position_qty * (run.position_avg_entry or 0))
            out.equity = eq
            out.return_pct = (
                (eq - run.starting_equity) / run.starting_equity * 100
                if run.starting_equity
                else 0
            )
            out.position_qty = run.position_qty
    return out


@router.get("", response_model=list[BotOut])
async def list_bots(request: Request, session: AsyncSession = Depends(get_db)):
    market = request.app.state.market
    bots = await bot_service.list_bots(session)
    return [await _bot_to_out(session, b, market) for b in bots]


@router.post("", response_model=BotOut)
async def create_bot(
    body: BotCreate, request: Request, session: AsyncSession = Depends(get_db)
):
    try:
        bot = await bot_service.create_bot(session, body.model_dump())
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    return await _bot_to_out(session, bot, request.app.state.market)


@router.get("/{bot_id}", response_model=BotOut)
async def get_bot(bot_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    bot = await bot_service.get_bot(session, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")
    return await _bot_to_out(session, bot, request.app.state.market)


@router.patch("/{bot_id}", response_model=BotOut)
async def patch_bot(
    bot_id: int,
    body: BotUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    bot = await bot_service.get_bot(session, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")
    try:
        bot = await bot_service.update_bot(
            session, bot, body.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return await _bot_to_out(session, bot, request.app.state.market)


@router.post("/{bot_id}/start", response_model=BotOut)
async def start_bot(
    bot_id: int, request: Request, session: AsyncSession = Depends(get_db)
):
    bot = await bot_service.get_bot(session, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")
    bot = await bot_service.start_bot(session, bot, _engine(request))
    return await _bot_to_out(session, bot, request.app.state.market)


@router.post("/{bot_id}/pause", response_model=BotOut)
async def pause_bot(
    bot_id: int, request: Request, session: AsyncSession = Depends(get_db)
):
    bot = await bot_service.get_bot(session, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")
    bot = await bot_service.pause_bot(session, bot, _engine(request))
    return await _bot_to_out(session, bot, request.app.state.market)


@router.post("/{bot_id}/stop", response_model=BotOut)
async def stop_bot(
    bot_id: int, request: Request, session: AsyncSession = Depends(get_db)
):
    bot = await bot_service.get_bot(session, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")
    bot = await bot_service.stop_bot(session, bot, _engine(request))
    return await _bot_to_out(session, bot, request.app.state.market)


@router.post("/{bot_id}/reset", response_model=BotOut)
async def reset_bot(
    bot_id: int, request: Request, session: AsyncSession = Depends(get_db)
):
    bot = await bot_service.get_bot(session, bot_id)
    if not bot:
        raise HTTPException(404, "Bot not found")
    bot = await bot_service.reset_bot(session, bot, _engine(request))
    return await _bot_to_out(session, bot, request.app.state.market)


@router.get("/{bot_id}/runs", response_model=list[RunSummary])
async def list_runs(bot_id: int, session: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    result = await session.execute(select(Run).where(Run.bot_id == bot_id).order_by(Run.id.desc()))
    return list(result.scalars().all())


@router.get("/runs/{run_id}/journal", response_model=list[JournalEventOut])
async def run_journal(run_id: int, session: AsyncSession = Depends(get_db)):
    from app.api.routes.journal import query_journal

    return await query_journal(session, run_id=run_id)


@router.get("/runs/{run_id}/equity-curve")
async def run_equity_curve(run_id: int, session: AsyncSession = Depends(get_db)):
    from app.services.compare_service import equity_curve

    return await equity_curve(session, run_id)
