"""
Base class for scoring plugins.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from analysis.score_result import ScoreResult


class BaseScore(ABC):
    """
    Abstract base class for scoring providers.
    """

    name = "base_score"

    @abstractmethod
    def calculate(self, context) -> ScoreResult:
        """
        Calculate one score from the supplied context.
        """
        raise NotImplementedError

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))
