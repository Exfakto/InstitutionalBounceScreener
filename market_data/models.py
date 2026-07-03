from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OhlcvRow:
    ticker: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str | None = None


@dataclass(frozen=True)
class MarketDataResult:
    success: bool
    ticker: str | None = None
    rows: list[OhlcvRow] = field(default_factory=list)
    data: object | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UniverseSymbol:
    ticker: str
    exchange: str | None = None
    security_type: str | None = None
    company_name: str | None = None


@dataclass(frozen=True)
class UniverseSymbolResult:
    success: bool
    symbols: list[UniverseSymbol] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
