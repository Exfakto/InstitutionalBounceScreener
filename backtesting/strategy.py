from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from backtesting.backtest_models import BacktestTrade


class BacktestStrategy(ABC):
    """
    Strategy contract for turning historical candidates into completed trades.
    """

    @abstractmethod
    def generate_trades(self, historical_candidates) -> Iterable[BacktestTrade]:
        """
        Return deterministic completed trades for the supplied historical data.
        """
