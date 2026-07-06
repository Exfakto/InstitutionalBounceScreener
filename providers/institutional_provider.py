"""
Provider-neutral institutional data models and provider interface.

Future real providers should implement InstitutionalProvider and return these
normalized models. Application services should depend on this module, not on a
vendor-specific response shape.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class InstitutionalOwnership:
    ticker: str
    ownership_pct: float | None = None
    holders_count: int | None = None
    as_of_date: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class OwnershipTrend:
    ticker: str
    change_qoq_pct: float | None = None
    holders_change: int | None = None
    trend_label: str | None = None
    as_of_date: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class InsiderActivity:
    ticker: str
    buying: bool | None = None
    selling: bool | None = None
    net_activity: float | None = None
    summary: str | None = None
    as_of_date: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class ThirteenFActivity:
    ticker: str
    net_buying: float | None = None
    accumulation_label: str | None = None
    summary: str | None = None
    major_buyers: list[str] = field(default_factory=list)
    major_sellers: list[str] = field(default_factory=list)
    as_of_date: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class ShortInterest:
    ticker: str
    short_interest_pct: float | None = None
    days_to_cover: float | None = None
    as_of_date: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class InstitutionalSnapshot:
    ticker: str
    status: str = "Not Configured"
    ownership: InstitutionalOwnership | None = None
    ownership_trend: OwnershipTrend | None = None
    thirteen_f: ThirteenFActivity | None = None
    insider_activity: InsiderActivity | None = None
    short_interest: ShortInterest | None = None
    provider_name: str | None = None
    warnings: list[str] = field(default_factory=list)


class InstitutionalProvider(ABC):
    """
    Abstract adapter for institutional data providers.
    """

    provider_name = "Institutional Provider"

    @abstractmethod
    def get_ownership(self, ticker: str) -> InstitutionalOwnership | None:
        raise NotImplementedError

    @abstractmethod
    def get_ownership_history(self, ticker: str) -> list[OwnershipTrend]:
        raise NotImplementedError

    @abstractmethod
    def get_13f_activity(self, ticker: str) -> ThirteenFActivity | None:
        raise NotImplementedError

    @abstractmethod
    def get_insider_activity(self, ticker: str) -> InsiderActivity | None:
        raise NotImplementedError

    @abstractmethod
    def get_short_interest(self, ticker: str) -> ShortInterest | None:
        raise NotImplementedError


class NoInstitutionalProvider(InstitutionalProvider):
    """
    Explicit no-provider adapter. It returns no data and raises no exceptions.
    """

    provider_name = "No Provider"

    def get_ownership(self, ticker):
        return None

    def get_ownership_history(self, ticker):
        return []

    def get_13f_activity(self, ticker):
        return None

    def get_insider_activity(self, ticker):
        return None

    def get_short_interest(self, ticker):
        return None
