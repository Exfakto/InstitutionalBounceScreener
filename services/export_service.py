from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


class ExportService:
    """
    Central export service for research and portfolio objects.
    """

    SUPPORTED_FORMATS = {"csv", "json"}
    RESEARCH_REPORT_FORMATS = {"json", "txt", "markdown"}

    def export_watchlist(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str = "csv",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        return self._export(
            data,
            destination_path,
            export_format,
            allow_overwrite,
            "Watchlist",
        )

    def export_trade_journal(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str = "csv",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        return self._export(
            data,
            destination_path,
            export_format,
            allow_overwrite,
            "Trade Journal",
        )

    def export_portfolio_statistics(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str = "json",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        return self._export(
            data,
            destination_path,
            export_format,
            allow_overwrite,
            "Portfolio Statistics",
        )

    def export_strategy_analytics(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str = "json",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        return self._export(
            data,
            destination_path,
            export_format,
            allow_overwrite,
            "Strategy Analytics",
        )

    def export_research_summary(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str = "json",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        return self._export(
            data,
            destination_path,
            export_format,
            allow_overwrite,
            "Research Preview",
        )

    def export_research_report(
        self,
        report: Any,
        destination_path: str | Path,
        format: str = "json",
        overwrite: bool = False,
    ) -> dict[str, Any]:
        normalized_format = self._normalize_format(format)

        if normalized_format not in self.RESEARCH_REPORT_FORMATS:
            return self._result(
                False,
                f"Unsupported export format: {format}.",
                export_format=normalized_format,
            )

        destination = self._destination_path(destination_path, normalized_format)

        if destination is None:
            return self._result(False, "Destination path is required.")

        if destination.exists() and not overwrite:
            return self._result(
                False,
                "Destination file already exists.",
                path=str(destination),
                export_format=normalized_format,
            )

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            normalized_report = self._normalize_data(report)

            if normalized_format == "json":
                self._write_json(normalized_report, destination)
            elif normalized_format == "txt":
                self._write_text_report(normalized_report, destination)
            else:
                self._write_markdown_report(normalized_report, destination)

            return self._result(
                True,
                "Research Report exported.",
                path=str(destination),
                export_format=normalized_format,
                count=self._count_records(normalized_report),
            )
        except OSError as exc:
            return self._result(
                False,
                f"Export failed: {exc}",
                path=str(destination),
                export_format=normalized_format,
            )
        except (TypeError, ValueError) as exc:
            return self._result(
                False,
                f"Export failed: {exc}",
                path=str(destination),
                export_format=normalized_format,
            )

    def _export(
        self,
        data: Any,
        destination_path: str | Path,
        export_format: str,
        allow_overwrite: bool,
        object_name: str,
    ) -> dict[str, Any]:
        normalized_format = self._normalize_format(export_format)

        if normalized_format not in self.SUPPORTED_FORMATS:
            return self._result(
                False,
                f"Unsupported export format: {export_format}.",
                export_format=normalized_format,
            )

        destination = self._destination_path(destination_path, normalized_format)

        if destination is None:
            return self._result(False, "Destination path is required.")

        if destination.exists() and not allow_overwrite:
            return self._result(
                False,
                "Destination file already exists.",
                path=str(destination),
                export_format=normalized_format,
            )

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            normalized_data = self._normalize_data(data)

            if normalized_format == "csv":
                self._write_csv(normalized_data, destination)
            else:
                self._write_json(normalized_data, destination)

            return self._result(
                True,
                f"{object_name} exported.",
                path=str(destination),
                export_format=normalized_format,
                count=self._count_records(normalized_data),
            )
        except OSError as exc:
            return self._result(
                False,
                f"Export failed: {exc}",
                path=str(destination),
                export_format=normalized_format,
            )
        except (TypeError, ValueError) as exc:
            return self._result(
                False,
                f"Export failed: {exc}",
                path=str(destination),
                export_format=normalized_format,
            )

    @classmethod
    def _write_csv(cls, data: Any, destination: Path) -> None:
        rows = cls._csv_rows(data)
        fieldnames = cls._fieldnames(rows)

        with destination.open("w", newline="", encoding="utf-8") as handle:
            if not fieldnames:
                handle.write("")
                return

            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_json(data: Any, destination: Path) -> None:
        destination.write_text(
            json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def _write_text_report(cls, data: Any, destination: Path) -> None:
        destination.write_text(cls._text_report(data), encoding="utf-8")

    @classmethod
    def _write_markdown_report(cls, data: Any, destination: Path) -> None:
        destination.write_text(cls._markdown_report(data), encoding="utf-8")

    @classmethod
    def _text_report(cls, data: Any) -> str:
        report = data if isinstance(data, dict) else {"report": data}
        title = report.get("title") or "Research Report"
        sections = [str(title)]

        for key, heading in cls._research_report_sections():
            value = report.get(key)
            if value in (None, "", []):
                continue
            sections.append(f"{heading}\n{cls._format_report_value(value)}")

        return "\n\n".join(sections).rstrip() + "\n"

    @classmethod
    def _markdown_report(cls, data: Any) -> str:
        report = data if isinstance(data, dict) else {"report": data}
        title = report.get("title") or "Research Report"
        sections = [f"# {title}"]

        for key, heading in cls._research_report_sections():
            value = report.get(key)
            if value in (None, "", []):
                continue
            sections.append(f"## {heading}\n\n{cls._format_report_value(value)}")

        return "\n\n".join(sections).rstrip() + "\n"

    @staticmethod
    def _research_report_sections() -> list[tuple[str, str]]:
        return [
            ("executive_summary", "Executive Summary"),
            ("setup_quality", "Setup Quality"),
            ("technical_analysis", "Technical Assessment"),
            ("fundamental_analysis", "Fundamental Assessment"),
            ("institutional_analysis", "Institutional Assessment"),
            ("trade_plan", "Trade Plan"),
            ("risk_summary", "Risk Assessment"),
            ("warnings", "Warnings"),
            ("conclusion", "Final Conclusion"),
            ("confidence", "Confidence"),
        ]

    @classmethod
    def _format_report_value(cls, value: Any) -> str:
        if isinstance(value, list):
            if not value:
                return ""
            return "\n".join(f"- {item}" for item in value)

        if isinstance(value, dict):
            return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)

        return str(value)

    @classmethod
    def _csv_rows(cls, data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [cls._flatten_record(item) for item in data]

        if isinstance(data, dict):
            if all(not isinstance(value, (dict, list)) for value in data.values()):
                return [cls._flatten_record(data)]

            return [
                {"field": key, "value": cls._stringify(value)}
                for key, value in data.items()
            ]

        if data is None:
            return []

        return [cls._flatten_record(data)]

    @classmethod
    def _fieldnames(cls, rows: list[dict[str, Any]]) -> list[str]:
        fieldnames: list[str] = []

        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)

        return fieldnames

    @classmethod
    def _normalize_data(cls, data: Any) -> Any:
        if data is None:
            return []

        if is_dataclass(data):
            return cls._normalize_data(asdict(data))

        if isinstance(data, dict):
            return {
                str(key): cls._normalize_data(value)
                for key, value in data.items()
            }

        if isinstance(data, (list, tuple)):
            return [cls._normalize_data(item) for item in data]

        if hasattr(data, "_asdict"):
            return cls._normalize_data(data._asdict())

        if hasattr(data, "__dict__") and not isinstance(data, (str, bytes)):
            return cls._normalize_data(vars(data))

        return data

    @classmethod
    def _flatten_record(cls, value: Any) -> dict[str, Any]:
        normalized = cls._normalize_data(value)

        if isinstance(normalized, dict):
            return {
                str(key): cls._stringify(item)
                for key, item in normalized.items()
            }

        return {"value": cls._stringify(normalized)}

    @staticmethod
    def _stringify(value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True, ensure_ascii=False)

        return value

    @staticmethod
    def _count_records(data: Any) -> int:
        if isinstance(data, list):
            return len(data)

        if isinstance(data, dict):
            return len(data)

        if data is None:
            return 0

        return 1

    @staticmethod
    def _destination_path(
        destination_path: str | Path,
        export_format: str,
    ) -> Path | None:
        if destination_path is None:
            return None

        path_text = str(destination_path).strip()

        if not path_text:
            return None

        destination = Path(path_text)

        suffix = ".md" if export_format == "markdown" else f".{export_format}"

        if destination.suffix.lower() != suffix:
            destination = destination.with_suffix(suffix)

        return destination

    @staticmethod
    def _normalize_format(export_format: str) -> str:
        return str(export_format or "").strip().lower()

    @staticmethod
    def _result(
        success: bool,
        message: str,
        path: str | None = None,
        export_format: str | None = None,
        count: int | None = None,
    ) -> dict[str, Any]:
        return {
            "success": success,
            "message": message,
            "path": path,
            "format": export_format,
            "count": count,
        }
