from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import JournalEventOut
from app.db.models import JournalEvent, JournalEventType, Run
from app.db.session import get_db

router = APIRouter(prefix="/journal", tags=["journal"])


async def query_journal(
    session: AsyncSession,
    *,
    run_id: int | None = None,
    bot_id: int | None = None,
    event_type: JournalEventType | None = None,
    timeframe: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 500,
) -> list[JournalEvent]:
    q = (
        select(JournalEvent)
        .join(Run, Run.id == JournalEvent.run_id)
        .order_by(JournalEvent.created_at.desc())
        .limit(limit)
    )
    if run_id is not None:
        q = q.where(JournalEvent.run_id == run_id)
    if bot_id is not None:
        q = q.where(JournalEvent.bot_id == bot_id)
    if event_type is not None:
        q = q.where(JournalEvent.event_type == event_type)
    if timeframe is not None:
        q = q.where(Run.timeframe == timeframe)
    if since is not None:
        q = q.where(JournalEvent.created_at >= since)
    if until is not None:
        q = q.where(JournalEvent.created_at <= until)
    result = await session.execute(q)
    return list(result.scalars().all())


@router.get("", response_model=list[JournalEventOut])
async def list_journal(
    session: AsyncSession = Depends(get_db),
    run_id: int | None = None,
    bot_id: int | None = None,
    event_type: JournalEventType | None = None,
    timeframe: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(500, ge=1, le=1000),
):
    return await query_journal(
        session,
        run_id=run_id,
        bot_id=bot_id,
        event_type=event_type,
        timeframe=timeframe,
        since=since,
        until=until,
        limit=limit,
    )
