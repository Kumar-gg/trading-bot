from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import DecisionLogOut
from app.db.models import DecisionLog, DecisionType
from app.db.session import get_db

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=list[DecisionLogOut])
async def list_decisions(
    session: AsyncSession = Depends(get_db),
    bot_id: int | None = None,
    decision: DecisionType | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    q = select(DecisionLog).order_by(DecisionLog.evaluated_at.desc()).limit(limit)
    if bot_id is not None:
        q = q.where(DecisionLog.bot_id == bot_id)
    if decision is not None:
        q = q.where(DecisionLog.decision == decision)
    if since is not None:
        q = q.where(DecisionLog.evaluated_at >= since)
    if until is not None:
        q = q.where(DecisionLog.evaluated_at <= until)
    result = await session.execute(q)
    return list(result.scalars().all())


@router.get("/latest/{bot_id}", response_model=DecisionLogOut | None)
async def latest_decision(bot_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(DecisionLog)
        .where(DecisionLog.bot_id == bot_id)
        .order_by(DecisionLog.evaluated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
