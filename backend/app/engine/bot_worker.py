import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Bot,
    BotHealthStatus,
    BotStatus,
    DecisionType,
    Fill,
    JournalEventType,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionLeg,
    Run,
)
from app.db.session import SessionLocal
from app.engine.events import StreamEvent, event_bus
from app.market.binance_ws import bar_index
from app.market.candles import candles_to_dataframe, load_candles, upsert_candles
from app.paper.broker import PaperBroker, order_side_for_signal_action
from app.paper.risk import RiskConfig, RiskManager
from app.services.decision_log import (
    build_checks_and_indicators,
    decision_from_signal,
    record_decision,
)
from app.services.health import refresh_bot_health
from app.services.journal import (
    log_regime_if_changed,
    log_strategy_evaluation,
    regime_table_payload,
    try_log_journal,
)
from app.strategies.indicators import compute_regime, enrich_bars
from app.strategies.registry import strategy_registry
from app.strategies.types import SignalAction, StrategyContext

logger = logging.getLogger(__name__)


class BotEngine:
    def __init__(self, market) -> None:
        self.market = market
        self.broker = PaperBroker()
        self.risk = RiskManager(RiskConfig())
        self._running_bot_ids: set[int] = set()
        market.add_handler(self._on_kline)

    async def sync_subscriptions(self, session: AsyncSession) -> None:
        result = await session.execute(
            select(Bot).where(Bot.status == BotStatus.running)
        )
        bots = result.scalars().all()
        self.market.unsubscribe_all()
        for bot in bots:
            self.market.subscribe(bot.symbol, bot.timeframe)
            try:
                await self._ensure_history(bot.symbol, bot.timeframe)
            except Exception:
                logger.exception("History backfill failed for %s %s", bot.symbol, bot.timeframe)
        self._running_bot_ids = {b.id for b in bots}
        if bots:
            logger.info("Resumed market subscriptions for %s running bot(s)", len(bots))

    async def refresh_all_health(self, session: AsyncSession) -> None:
        result = await session.execute(select(Bot))
        for bot in result.scalars():
            age = self.market.market_data_age_sec(bot.symbol, bot.timeframe)
            if bot.status != BotStatus.running:
                bot.health_status = BotHealthStatus.idle
            else:
                refresh_bot_health(bot, age)
        await session.commit()

    async def _ensure_history(self, symbol: str, timeframe: str) -> None:
        async with SessionLocal() as session:
            existing = await load_candles(session, symbol, timeframe, limit=10)
            if len(existing) >= 10:
                return
        candles = await self.market.fetch_historical_klines(symbol, timeframe, 500)
        if not candles:
            logger.warning("No klines fetched for %s %s", symbol, timeframe)
            return
        async with SessionLocal() as session:
            await upsert_candles(session, symbol, timeframe, candles)
            await session.commit()

    async def _on_kline(
        self, symbol: str, timeframe: str, candle, is_closed: bool
    ) -> None:
        if not is_closed:
            return
        self.market.mark_stream_update(symbol, timeframe)
        async with SessionLocal() as session:
            await upsert_candles(session, symbol, timeframe, [candle])
            await session.commit()

        async with SessionLocal() as session:
            result = await session.execute(
                select(Bot).where(
                    Bot.status == BotStatus.running,
                    Bot.symbol == symbol,
                    Bot.timeframe == timeframe,
                )
            )
            bots = result.scalars().all()
            for bot in bots:
                await self._evaluate_bot(session, bot, candle)

    async def _evaluate_bot(self, session: AsyncSession, bot: Bot, candle) -> None:
        if not bot.current_run_id:
            return
        run = await session.get(Run, bot.current_run_id)
        if not run or run.ended_at:
            return
        if run.last_bar_time == candle.open_time:
            return

        mkt_ts = self.market.last_market_update_at(bot.symbol, bot.timeframe)
        if mkt_ts:
            bot.last_market_data_at = mkt_ts
        mkt_age = self.market.market_data_age_sec(bot.symbol, bot.timeframe)
        btc_price = self.market.get_btc_price()
        mark = candle.close

        try:
            stop_side = self.broker.check_stops(run, candle.high, candle.low)
            if stop_side:
                await self._execute_market(
                    session,
                    bot,
                    run,
                    stop_side,
                    run.position_qty or 0,
                    mark,
                    "Stop/TP hit",
                    candle_open_time=candle.open_time,
                )
                await record_decision(
                    session,
                    bot,
                    run,
                    candle_open_time=candle.open_time,
                    symbol_price=mark,
                    btc_price=btc_price,
                    market_data_age_sec=mkt_age,
                    checks=[],
                    decision=DecisionType.SELL,
                    reason="Stop or take-profit level hit",
                    indicators={"mark_price": mark},
                )
                await self._journal_evaluation(
                    session,
                    bot,
                    run,
                    candle,
                    DecisionType.SELL,
                    "Stop or take-profit level hit",
                    {"mark_price": mark},
                )

            candles = await load_candles(session, bot.symbol, bot.timeframe, 500)
            df = enrich_bars(candles_to_dataframe(candles))
            equity = self.broker.mark_equity(run, mark)
            if equity > run.peak_equity:
                run.peak_equity = equity

            template = strategy_registry.get(bot.template_id)
            params = strategy_registry.parse_params(bot.template_id, bot.params)
            ctx = StrategyContext(
                symbol=bot.symbol,
                timeframe=bot.timeframe,
                bars=df,
                position_qty=run.position_qty or 0,
                position_avg_entry=run.position_avg_entry,
                equity=equity,
                cash=run.cash,
                mark_price=mark,
            )
            checks, indicators = build_checks_and_indicators(bot.template_id, ctx, params)

            if df.empty:
                await record_decision(
                    session,
                    bot,
                    run,
                    candle_open_time=candle.open_time,
                    symbol_price=mark,
                    btc_price=btc_price,
                    market_data_age_sec=mkt_age,
                    checks=checks,
                    decision=DecisionType.HOLD,
                    reason="No candle history available",
                    rejection_source="data",
                    indicators=indicators,
                )
                await self._journal_evaluation(
                    session,
                    bot,
                    run,
                    candle,
                    DecisionType.HOLD,
                    "No candle history available",
                    indicators,
                )
                run.last_bar_time = candle.open_time
                await session.commit()
                return

            warmup = template.warmup_bars(params)
            if len(df) < warmup:
                await record_decision(
                    session,
                    bot,
                    run,
                    candle_open_time=candle.open_time,
                    symbol_price=mark,
                    btc_price=btc_price,
                    market_data_age_sec=mkt_age,
                    checks=checks,
                    decision=DecisionType.HOLD,
                    reason=f"Warmup incomplete ({len(df)}/{warmup} bars)",
                    indicators=indicators,
                )
                await self._journal_evaluation(
                    session,
                    bot,
                    run,
                    candle,
                    DecisionType.HOLD,
                    f"Warmup incomplete ({len(df)}/{warmup} bars)",
                    indicators,
                )
                run.last_bar_time = candle.open_time
                await session.commit()
                return

            bar_regime = compute_regime(df.iloc[-1])
            await log_regime_if_changed(
                session,
                run,
                bot.id,
                bot.symbol,
                bot.timeframe,
                candle.open_time,
                bar_regime,
            )

            signal = template.on_bar(ctx, params)
            idx = bar_index(candle.open_time, bot.timeframe)
            decision = decision_from_signal(signal)
            reason = signal.reason if signal else "No entry/exit signal on this bar"
            rejection_source = None
            rejection_detail = None

            if signal:
                await try_log_journal(
                    session,
                    run,
                    JournalEventType.signal,
                    signal.reason,
                    {
                        "action": signal.action.value,
                        "metadata": signal.metadata,
                        "candle_open_time": candle.open_time,
                    },
                    dedupe_key=f"signal:{candle.open_time}",
                    bot_id=bot.id,
                )
                if signal.action == SignalAction.buy:
                    risk_decision = self.risk.evaluate_entry(
                        signal,
                        equity,
                        mark,
                        run.position_qty or 0,
                        idx,
                        run.cooldown_until_bar,
                        run.starting_equity,
                        run.peak_equity,
                    )
                    if not risk_decision.allowed:
                        decision = DecisionType.REJECTED
                        reason = signal.reason
                        rejection_source = "risk"
                        rejection_detail = risk_decision.reason
                        await try_log_journal(
                            session,
                            run,
                            JournalEventType.risk_rejected,
                            risk_decision.reason,
                            {
                                "candle_open_time": candle.open_time,
                                "signal_action": signal.action.value,
                            },
                            dedupe_key=f"risk:{candle.open_time}",
                            bot_id=bot.id,
                        )
                        if "drawdown" in risk_decision.reason.lower() or "loss limit" in risk_decision.reason.lower():
                            bot.status = BotStatus.paused
                            bot.health_status = BotHealthStatus.idle
                            await try_log_journal(
                                session,
                                run,
                                JournalEventType.bot_paused,
                                risk_decision.reason,
                                dedupe_key=f"paused:{candle.open_time}",
                                bot_id=bot.id,
                            )
                    else:
                        side = order_side_for_signal_action(signal.action.value)
                        await self._execute_market(
                            session,
                            bot,
                            run,
                            side,
                            risk_decision.qty,
                            mark,
                            signal.reason,
                            candle_open_time=candle.open_time,
                            regime=bar_regime,
                        )
                        if run.position_avg_entry and signal.stop_loss_pct:
                            self.broker.set_bracket(
                                run,
                                run.position_avg_entry,
                                signal.stop_loss_pct,
                                signal.take_profit_pct,
                            )
                        decision = DecisionType.BUY
                        reason = signal.reason
                elif signal.action in (SignalAction.close, SignalAction.sell):
                    if (run.position_qty or 0) > 0:
                        await self._execute_market(
                            session,
                            bot,
                            run,
                            OrderSide.sell,
                            run.position_qty,
                            mark,
                            signal.reason,
                            candle_open_time=candle.open_time,
                            regime=bar_regime,
                        )
                        decision = DecisionType.SELL
                        reason = signal.reason
                        cooldown = self.risk.config.cooldown_bars
                        if cooldown:
                            run.cooldown_until_bar = idx + cooldown
                    else:
                        decision = DecisionType.HOLD
                        reason = "Exit signal but no open position"

            await record_decision(
                session,
                bot,
                run,
                candle_open_time=candle.open_time,
                symbol_price=mark,
                btc_price=btc_price,
                market_data_age_sec=mkt_age,
                checks=checks,
                decision=decision,
                reason=reason,
                rejection_source=rejection_source,
                rejection_detail=rejection_detail,
                indicators=indicators,
            )
            await self._journal_evaluation(
                session,
                bot,
                run,
                candle,
                decision,
                reason,
                indicators,
                rejection_source=rejection_source,
                rejection_detail=rejection_detail,
            )

            run.last_bar_time = candle.open_time
            await session.commit()
            await event_bus.publish(
                StreamEvent(
                    type="bot_update",
                    payload={"bot_id": bot.id, "equity": self.broker.mark_equity(run, mark)},
                )
            )
        except Exception as exc:
            logger.exception("Bot evaluation failed bot_id=%s", bot.id)
            bot.last_eval_error = str(exc)
            bot.health_status = BotHealthStatus.error
            bot.last_evaluation_at = datetime.now(timezone.utc)
            try:
                await record_decision(
                    session,
                    bot,
                    run,
                    candle_open_time=candle.open_time,
                    symbol_price=mark,
                    btc_price=btc_price,
                    market_data_age_sec=mkt_age,
                    checks=[],
                    decision=DecisionType.REJECTED,
                    reason="Evaluation error",
                    rejection_source="execution",
                    rejection_detail=str(exc),
                )
                run.last_bar_time = candle.open_time
                await session.commit()
            except Exception:
                await session.rollback()

    async def _journal_evaluation(
        self,
        session: AsyncSession,
        bot: Bot,
        run: Run,
        candle,
        decision: DecisionType,
        reason: str,
        indicators: dict,
        *,
        rejection_source: str | None = None,
        rejection_detail: str | None = None,
    ) -> None:
        await log_strategy_evaluation(
            session,
            run,
            bot.id,
            candle_open_time=candle.open_time,
            decision=decision.value,
            reason=reason,
            symbol=bot.symbol,
            timeframe=bot.timeframe,
            indicators=indicators,
            rejection_source=rejection_source,
            rejection_detail=rejection_detail,
        )

    async def _execute_market(
        self,
        session: AsyncSession,
        bot: Bot,
        run: Run,
        side: OrderSide,
        qty: float,
        mark: float,
        reason: str,
        *,
        candle_open_time: int | None = None,
        regime: dict | None = None,
    ) -> None:
        if qty <= 0:
            return
        bar_time = candle_open_time or run.last_bar_time or 0
        await try_log_journal(
            session,
            run,
            JournalEventType.order_placed,
            f"Simulated {side.value} order {qty:.6f} @ ~{mark:.2f}",
            {
                "side": side.value,
                "qty": qty,
                "mark_price": mark,
                "candle_open_time": bar_time,
            },
            dedupe_key=f"order:{bar_time}:{side.value}:{qty:.8f}",
            bot_id=bot.id,
        )
        fill_result = self.broker.market_fill(side, qty, mark)
        order = Order(
            run_id=run.id,
            side=side,
            order_type=OrderType.market,
            qty=fill_result.qty,
            status=OrderStatus.filled,
        )
        session.add(order)
        await session.flush()
        fill = Fill(
            order_id=order.id,
            run_id=run.id,
            price=fill_result.price,
            qty=fill_result.qty,
            fee=fill_result.fee,
            slippage_bps=fill_result.slippage_bps,
        )
        session.add(fill)
        position_leg: PositionLeg | None = None
        trade_group_id: str | None = run.active_trade_group_id
        if side == OrderSide.buy:
            run.active_trade_group_id = run.active_trade_group_id or str(uuid.uuid4())
            trade_group_id = run.active_trade_group_id
            position_leg = PositionLeg.entry
        elif side == OrderSide.sell and (run.position_qty or 0) > 0:
            position_leg = PositionLeg.exit

        fill.candle_open_time = bar_time
        fill.regime_snapshot = regime
        fill.position_leg = position_leg
        fill.trade_group_id = trade_group_id
        await session.flush()

        self.broker.apply_fill_to_run(run, side, fill_result)
        if side == OrderSide.sell and (run.position_qty or 0) <= 0:
            run.active_trade_group_id = None

        await try_log_journal(
            session,
            run,
            JournalEventType.fill,
            reason,
            {
                "side": side.value,
                "qty": fill_result.qty,
                "price": fill_result.price,
                "fee": fill_result.fee,
                "candle_open_time": bar_time,
                "trade_group_id": trade_group_id,
                "position_leg": position_leg.value if position_leg else None,
                "regime_snapshot": regime,
                "fill_id": fill.id,
            },
            dedupe_key=f"fill:{bar_time}:{side.value}:{fill_result.qty:.8f}",
            bot_id=bot.id,
        )
        if side == OrderSide.sell and position_leg == PositionLeg.exit:
            await try_log_journal(
                session,
                run,
                JournalEventType.position_exit,
                reason,
                {
                    "candle_open_time": bar_time,
                    "trade_group_id": trade_group_id,
                    "exit_regime": regime,
                    **regime_table_payload(
                        symbol=bot.symbol,
                        timeframe=bot.timeframe,
                        candle_open_time=bar_time,
                        regime=regime or {},
                    ),
                },
                dedupe_key=f"exit:{bar_time}",
                bot_id=bot.id,
            )
