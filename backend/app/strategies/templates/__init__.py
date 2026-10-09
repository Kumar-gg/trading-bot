from app.strategies.templates.bb_mean_revert import BbMeanRevertStrategy
from app.strategies.templates.donchian_breakout import DonchianBreakoutStrategy
from app.strategies.templates.ema_trend import EmaTrendStrategy
from app.strategies.templates.macd_trend import MacdTrendStrategy
from app.strategies.templates.rsi_pullback import RsiPullbackStrategy
from app.strategies.templates.squeeze_breakout import SqueezeBreakoutStrategy
from app.strategies.templates.supertrend_trail import SupertrendTrailStrategy

ALL_TEMPLATES = [
    EmaTrendStrategy(),
    RsiPullbackStrategy(),
    DonchianBreakoutStrategy(),
    MacdTrendStrategy(),
    BbMeanRevertStrategy(),
    SqueezeBreakoutStrategy(),
    SupertrendTrailStrategy(),
]
