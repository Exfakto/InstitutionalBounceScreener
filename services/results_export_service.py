from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path


RANKED_CANDIDATE_EXPORT_FIELDS = [
    "rank",
    "ticker",
    "final_score",
    "grade",
    "confidence_level",
    "setup_label",
    "explanation",
    "warnings",
    "rejection_reasons",
    "run_id",
    "created_at",
]


class ResultsExportService:
    """
    Export ranked institutional bounce results and screening run metadata.
    """

    def export_ranked_candidates_csv(self, candidates, output_dir, filename):
        destination = self.destination_path(output_dir, filename, "csv")
        if destination is None:
            return self.result(False, "Output directory is required.")

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            rows = [self.candidate_row(candidate) for candidate in (candidates or [])]
            with destination.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=RANKED_CANDIDATE_EXPORT_FIELDS,
                )
                writer.writeheader()
                writer.writerows(rows)
            return self.result(
                True,
                "Ranked candidates exported to CSV.",
                path=destination,
                count=len(rows),
            )
        except OSError as exc:
            return self.result(False, f"Export failed: {exc}", path=destination)

    def export_ranked_candidates_json(self, candidates, output_dir, filename):
        destination = self.destination_path(output_dir, filename, "json")
        if destination is None:
            return self.result(False, "Output directory is required.")

        rows = [self.candidate_row(candidate) for candidate in (candidates or [])]
        return self.write_json(
            rows,
            destination,
            "Ranked candidates exported to JSON.",
            count=len(rows),
        )

    def export_screening_run_metadata_json(self, run_metadata, output_dir, filename):
        destination = self.destination_path(output_dir, filename, "json")
        if destination is None:
            return self.result(False, "Output directory is required.")

        return self.write_json(
            self.normalize_run_metadata(run_metadata),
            destination,
            "Screening run metadata exported to JSON.",
        )

    def export_full_run_package(
        self,
        run_metadata,
        candidates,
        output_dir,
        filename,
        provider_metadata=None,
    ):
        destination = self.destination_path(output_dir, filename, "json")
        if destination is None:
            return self.result(False, "Output directory is required.")

        package = {
            "run": self.normalize_run_metadata(run_metadata),
            "candidates": [
                self.candidate_row(candidate) for candidate in (candidates or [])
            ],
            "provider_metadata": self.normalize_run_metadata(provider_metadata),
        }
        return self.write_json(
            package,
            destination,
            "Full screening run package exported.",
            count=len(package["candidates"]),
        )

    def export_cache_coverage_report(self, coverage_rows, output_dir, filename):
        destination = self.destination_path(output_dir, filename, "json")
        if destination is None:
            return self.result(False, "Output directory is required.")
        payload = [self.normalize_run_metadata(row) for row in (coverage_rows or [])]
        return self.write_json(
            payload,
            destination,
            "Cache coverage report exported.",
            count=len(payload),
        )

    def export_data_quality_report(self, report, output_dir, filename):
        destination = self.destination_path(output_dir, filename, "json")
        if destination is None:
            return self.result(False, "Output directory is required.")
        payload = self.normalize_run_metadata(report)
        return self.write_json(
            payload,
            destination,
            "Data quality report exported.",
            count=len(payload.get("ticker_reports", {}) if isinstance(payload, dict) else []),
        )

    def export_backtest_summary_json(self, backtest_run, output_dir, filename):
        destination = self.destination_path(output_dir, filename, "json")
        if destination is None:
            return self.result(False, "Output directory is required.")
        payload = self.normalize_run_metadata(backtest_run)
        return self.write_json(
            payload,
            destination,
            "Backtest summary exported.",
            count=len(payload.get("trades", []) if isinstance(payload, dict) else []),
        )

    def export_backtest_trades_csv(self, trades, output_dir, filename):
        destination = self.destination_path(output_dir, filename, "csv")
        if destination is None:
            return self.result(False, "Output directory is required.")
        fields = [
            "ticker",
            "entry_date",
            "exit_date",
            "entry_price",
            "exit_price",
            "return_pct",
            "max_gain_pct",
            "max_drawdown_pct",
            "holding_days",
            "exit_reason",
            "final_score",
            "grade",
            "confidence_level",
            "setup_label",
            "source_run_id",
            "signal_date",
            "warnings",
        ]
        rows = [self.backtest_trade_row(trade) for trade in (trades or [])]
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            return self.result(
                True,
                "Backtest trades exported to CSV.",
                path=destination,
                count=len(rows),
            )
        except OSError as exc:
            return self.result(False, f"Export failed: {exc}", path=destination)

    def export_chart_data_json(self, chart_model, output_dir, filename):
        destination = self.destination_path(output_dir, filename, "json")
        if destination is None:
            return self.result(False, "Output directory is required.")
        return self.write_json(
            self.normalize_run_metadata(chart_model),
            destination,
            "Chart data exported.",
        )

    def export_equity_curve_csv(self, equity_curve, output_dir, filename):
        return self.export_series_csv(
            equity_curve,
            output_dir,
            filename,
            ["date", "equity", "cumulative_return_pct"],
            "Equity curve exported.",
        )

    def export_drawdown_curve_csv(self, drawdown_curve, output_dir, filename):
        return self.export_series_csv(
            drawdown_curve,
            output_dir,
            filename,
            ["date", "drawdown_pct"],
            "Drawdown curve exported.",
        )

    def export_backtest_analytics_json(self, analytics_model, output_dir, filename):
        destination = self.destination_path(output_dir, filename, "json")
        if destination is None:
            return self.result(False, "Output directory is required.")
        return self.write_json(
            self.normalize_run_metadata(analytics_model),
            destination,
            "Backtest analytics exported.",
        )

    def export_series_csv(self, rows, output_dir, filename, fields, message):
        destination = self.destination_path(output_dir, filename, "csv")
        if destination is None:
            return self.result(False, "Output directory is required.")
        normalized = [self.normalize_run_metadata(row) for row in (rows or [])]
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for row in normalized:
                    writer.writerow({field: row.get(field) for field in fields})
            return self.result(True, message, path=destination, count=len(normalized))
        except OSError as exc:
            return self.result(False, f"Export failed: {exc}", path=destination)

    def write_json(self, payload, destination, message, count=None):
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
            )
            return self.result(True, message, path=destination, count=count)
        except OSError as exc:
            return self.result(False, f"Export failed: {exc}", path=destination)

    @classmethod
    def candidate_row(cls, candidate):
        source = cls.value(candidate, "source") or {}
        return {
            "rank": cls.value(candidate, "rank"),
            "ticker": cls.value(candidate, "ticker"),
            "final_score": cls.value(candidate, "final_score"),
            "grade": cls.value(candidate, "grade"),
            "confidence_level": cls.value(candidate, "confidence_level"),
            "setup_label": cls.value(candidate, "setup_label"),
            "explanation": cls.list_text(cls.value(candidate, "explanation")),
            "warnings": cls.list_text(cls.value(candidate, "warnings")),
            "rejection_reasons": cls.list_text(cls.value(candidate, "rejection_reasons")),
            "run_id": cls.first_existing(
                cls.value(candidate, "run_id"),
                cls.value(source, "run_id"),
            ),
            "created_at": cls.first_existing(
                cls.value(candidate, "created_at"),
                cls.value(source, "created_at"),
            ),
        }

    @classmethod
    def backtest_trade_row(cls, trade):
        return {
            "ticker": cls.value(trade, "ticker"),
            "entry_date": cls.value(trade, "entry_date"),
            "exit_date": cls.value(trade, "exit_date"),
            "entry_price": cls.value(trade, "entry_price"),
            "exit_price": cls.value(trade, "exit_price"),
            "return_pct": cls.value(trade, "return_pct"),
            "max_gain_pct": cls.value(trade, "max_gain_pct"),
            "max_drawdown_pct": cls.value(trade, "max_drawdown_pct"),
            "holding_days": cls.value(trade, "holding_days"),
            "exit_reason": cls.value(trade, "exit_reason"),
            "final_score": cls.value(trade, "final_score"),
            "grade": cls.value(trade, "grade"),
            "confidence_level": cls.value(trade, "confidence_level"),
            "setup_label": cls.value(trade, "setup_label"),
            "source_run_id": cls.value(trade, "source_run_id"),
            "signal_date": cls.value(trade, "signal_date"),
            "warnings": cls.list_text(cls.value(trade, "warnings")),
        }

    @classmethod
    def normalize_run_metadata(cls, run_metadata):
        if run_metadata is None:
            return {}
        if is_dataclass(run_metadata):
            return cls.normalize_run_metadata(asdict(run_metadata))
        if isinstance(run_metadata, dict):
            return {
                str(key): cls.json_safe(value)
                for key, value in run_metadata.items()
            }
        if hasattr(run_metadata, "__dict__"):
            return cls.normalize_run_metadata(vars(run_metadata))
        return {"value": cls.json_safe(run_metadata)}

    @classmethod
    def json_safe(cls, value):
        if is_dataclass(value):
            return cls.json_safe(asdict(value))
        if isinstance(value, dict):
            return {str(key): cls.json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls.json_safe(item) for item in value]
        return value

    @staticmethod
    def destination_path(output_dir, filename, extension):
        if output_dir in (None, ""):
            return None
        directory = Path(str(output_dir))
        safe_name = ResultsExportService.sanitize_filename(filename or "export")
        destination = directory / safe_name
        suffix = f".{extension}"
        if destination.suffix.lower() != suffix:
            destination = destination.with_suffix(suffix)
        return destination

    @staticmethod
    def sanitize_filename(filename):
        stem = Path(str(filename or "export")).stem
        sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._")
        return sanitized or "export"

    @staticmethod
    def list_text(value):
        if value in (None, ""):
            return ""
        if isinstance(value, (list, tuple)):
            return "; ".join(str(item) for item in value)
        return str(value)

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def result(success, message, path=None, count=None):
        return {
            "success": success,
            "message": message,
            "path": str(path) if path is not None else None,
            "count": count,
        }
