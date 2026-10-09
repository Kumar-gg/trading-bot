from fastapi import APIRouter, Request

from app.api.schemas import SettingsOut
from app.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(request: Request):
    market = request.app.state.market
    return SettingsOut(
        fee_bps=settings.default_fee_bps,
        slippage_bps=settings.default_slippage_bps,
        market_connected=market._running and market.rest_ok,
        rest_ok=market.rest_ok,
        ws_connected=market.ws_connected,
        last_error=market.last_error,
    )
