import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import bots, compare, decisions, journal, settings, strategies, stream
from app.config import settings as app_settings
from app.db.session import SessionLocal, init_db
from app.engine.bot_worker import BotEngine
from app.market.binance_ws import MarketDataService
from app.services.bot_service import snapshot_equity_for_runs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _equity_loop(market: MarketDataService, engine: BotEngine) -> None:
    while True:
        try:
            async with SessionLocal() as session:
                await snapshot_equity_for_runs(session, market)
                await engine.refresh_all_health(session)
        except Exception:
            logger.exception("Equity snapshot failed")
        await asyncio.sleep(app_settings.equity_snapshot_interval_sec)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    market = MarketDataService()
    engine = BotEngine(market)
    app.state.market = market
    app.state.engine = engine
    await market.start()
    try:
        async with SessionLocal() as session:
            await engine.sync_subscriptions(session)
    except Exception:
        logger.exception("Initial bot sync failed (API still starting; market may be offline)")
    equity_task = asyncio.create_task(_equity_loop(market, engine))
    yield
    equity_task.cancel()
    try:
        await equity_task
    except asyncio.CancelledError:
        pass
    await market.stop()


app = FastAPI(title="Trading Bot Paper API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bots.router, prefix="/api")
app.include_router(decisions.router, prefix="/api")
app.include_router(journal.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(compare.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(stream.router, prefix="/api")


@app.get("/api/health")
async def health(request: Request):
    market = request.app.state.market
    return {
        "status": "ok",
        "market_rest": market.rest_ok,
        "market_ws": market.ws_connected,
        "market_error": market.last_error,
    }
