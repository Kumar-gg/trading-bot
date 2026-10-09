from fastapi import APIRouter

from app.api.schemas import StrategyOut
from app.strategies.registry import strategy_registry

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", response_model=list[StrategyOut])
def list_strategies():
    out = []
    for meta in strategy_registry.list_metadata():
        out.append(
            StrategyOut(
                id=meta.id,
                name=meta.name,
                description=meta.description,
                category=meta.category,
                supported_timeframes=meta.supported_timeframes,
                params_schema=strategy_registry.params_schema(meta.id),
            )
        )
    return out
