from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

from services.app_config_service import AppConfigService
from services.model_calibration_recommendation_service import (
    ModelCalibrationRecommendationService,
    recommendation_to_dict,
)


class BetaReportExportService:
    """Export beta reports while preserving existing beta export payloads."""

    def __init__(self, app_config_service=None, calibration_recommendation_service=None):
        self.app_config_service = app_config_service or AppConfigService()
        self.calibration_recommendation_service = (
            calibration_recommendation_service
            or ModelCalibrationRecommendationService()
        )

    def export_all(self, result, output_dir=None, basename=None, calibration_run_id=None):
        run = value(result, "run")
        run_id = value(run, "run_id") or "beta"
        basename = basename or run_id
        calibration_recommendations = self.calibration_recommendations(
            result, calibration_run_id=calibration_run_id
        )
        return {
            "summary_json": self.export_run_summary_json(
                result,
                output_dir,
                f"{basename}_summary.json",
                calibration_recommendations=calibration_recommendations,
            )["path"],
            "review_pack_json": self.export_review_pack_json(
                value(result, "review_pack") or value(result, "candidates") or [],
                output_dir,
                f"{basename}_review_pack.json",
                calibration_recommendations=calibration_recommendations,
            )["path"],
            "review_pack_csv": self.export_review_pack_csv(
                value(result, "review_pack") or value(result, "candidates") or [],
                output_dir,
                f"{basename}_review_pack.csv",
            )["path"],
            "checklist_csv": self.export_manual_checklist_csv(
                value(result, "checklist") or [],
                output_dir,
                f"{basename}_manual_checklist.csv",
            )["path"],
        }

    def export_run_summary_json(
        self,
        result,
        output_dir=None,
        filename="beta_run_summary.json",
        calibration_recommendations=None,
    ):
        path = self.destination(output_dir, filename)
        payload = json_safe(result)
        payload["calibration_recommendations"] = list(
            calibration_recommendations
            if calibration_recommendations is not None
            else self.calibration_recommendations(result)
        )
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return {"success": True, "path": str(path)}

    def export_review_pack_json(
        self,
        review_pack,
        output_dir=None,
        filename="candidate_review_pack.json",
        calibration_recommendations=None,
    ):
        path = self.destination(output_dir, filename)
        candidates = candidate_rows(review_pack)
        payload = {
            "candidates": json_safe(candidates),
            "calibration_recommendations": list(
                calibration_recommendations
                if calibration_recommendations is not None
                else self.calibration_recommendations(review_pack)
            ),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return {"success": True, "path": str(path), "count": len(candidates)}

    def export_review_pack_csv(
        self,
        review_pack,
        output_dir=None,
        filename="candidate_review_pack.csv",
    ):
        path = self.destination(output_dir, filename)
        fields = [
            "ticker",
            "grade",
            "score",
            "setup_label",
            "support_zone_summary",
            "bounce_history_summary",
            "institutional_summary",
            "chart_data_available",
            "warnings",
        ]
        rows = []
        for item in candidate_rows(review_pack):
            row = json_safe(item)
            row["warnings"] = "; ".join(str(entry) for entry in row.get("warnings") or [])
            rows.append(row)
        self.write_csv(path, fields, rows)
        return {"success": True, "path": str(path), "count": len(rows)}

    def export_manual_checklist_csv(
        self,
        checklist,
        output_dir=None,
        filename="manual_review_checklist.csv",
    ):
        path = self.destination(output_dir, filename)
        fields = [
            "ticker",
            "chart_confirms_support",
            "volume_confirms_accumulation",
            "no_earnings_risk",
            "sector_market_trend_acceptable",
            "risk_reward_acceptable",
            "decision",
            "notes",
        ]
        rows = [json_safe(item) for item in (checklist or [])]
        self.write_csv(path, fields, rows)
        return {"success": True, "path": str(path), "count": len(rows)}

    def calibration_recommendations(self, source=None, calibration_run_id=None):
        embedded = value(source, "calibration_recommendations")
        if embedded is not None:
            return [recommendation_to_dict(item) for item in embedded]
        return [
            recommendation_to_dict(item)
            for item in self.calibration_recommendation_service.get_recommendations(
                run_id=calibration_run_id
            )
        ]

    def destination(self, output_dir, filename):
        directory = Path(output_dir or self.app_config_service.load().export_directory)
        directory.mkdir(parents=True, exist_ok=True)
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in str(filename))
        return directory / safe

    @staticmethod
    def write_csv(path, fields, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


def candidate_rows(review_pack):
    if review_pack is None:
        return []
    candidates = value(review_pack, "candidates", None)
    if candidates is not None:
        return list(candidates or [])
    return list(review_pack or [])


def json_safe(raw):
    if is_dataclass(raw):
        return json_safe(asdict(raw))
    if isinstance(raw, dict):
        return {str(key): json_safe(value) for key, value in raw.items()}
    if isinstance(raw, (list, tuple)):
        return [json_safe(item) for item in raw]
    return raw


def value(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)
