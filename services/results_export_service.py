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
