from dataclasses import dataclass


@dataclass(frozen=True)
class InstitutionalData:
    ticker: str
    institutional_ownership_pct: float | None = None
    institutional_ownership_change_qoq: float | None = None
    net_institutional_buying: float | None = None
    insider_buying_flag: int = 0
    insider_selling_flag: int = 0
    source: str | None = None
    as_of_date: str | None = None
    updated_at: str | None = None
