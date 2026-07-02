from __future__ import annotations

from pathlib import Path
from typing import Any

from services.export_service import ExportService


class ExportController:
    """
    Thin controller for export operations.
    """

    def __init__(self, export_service: ExportService | None = None) -> None:
        self.export_service = export_service or ExportService()

    def export_watchlist(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str = "csv",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        return self.export_service.export_watchlist(
            data,
            destination_path,
            export_format,
            allow_overwrite,
        )

    def export_trade_journal(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str = "csv",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        return self.export_service.export_trade_journal(
            data,
            destination_path,
            export_format,
            allow_overwrite,
        )

    def export_portfolio_statistics(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str = "json",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        return self.export_service.export_portfolio_statistics(
            data,
            destination_path,
            export_format,
            allow_overwrite,
        )

    def export_strategy_analytics(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str = "json",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        return self.export_service.export_strategy_analytics(
            data,
            destination_path,
            export_format,
            allow_overwrite,
        )

    def export_research_summary(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str = "json",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        return self.export_service.export_research_summary(
            data,
            destination_path,
            export_format,
            allow_overwrite,
        )

    def export_research_report(
        self,
        report: Any,
        destination_path: str | Path,
        format: str = "json",
        overwrite: bool = False,
    ) -> dict[str, Any]:
        return self.export_service.export_research_report(
            report,
            destination_path,
            format,
            overwrite,
        )
