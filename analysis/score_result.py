"""
Score result model.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScoreResult:
    """
    Value object returned by score providers.
    """

    name: str
    value: float
    details: dict = field(default_factory=dict)
    error: str | None = None

    @property
    def failed(self):
        return self.error is not None
