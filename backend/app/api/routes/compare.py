from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import CompareRequest
from app.db.session import get_db
from app.services.compare_service import compare_runs

router = APIRouter(prefix="/compare", tags=["compare"])


@router.post("")
async def compare(body: CompareRequest, session: AsyncSession = Depends(get_db)):
    return await compare_runs(session, body.run_ids)
