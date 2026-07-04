from __future__ import annotations

from dataclasses import dataclass, field


CONFIDENCE_LEVELS = {"LOW", "MEDIUM", "HIGH"}
THRESHOLD_KEYS = {
    "minimum_final_score": "calibration.minimum_final_score",
    "minimum_support_score": "calibration.minimum_support_score",
    "minimum_bounce_score": "calibration.minimum_bounce_score",
    "minimum_technical_score": "calibration.minimum_technical_score",
    "minimum_institutional_score": "calibration.minimum_institutional_score",
}


@dataclass(frozen=True)
class CalibrationApplyResult:
    status: str
    applied: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    message: str = ""


class ModelCalibrationApplyService:
    """Apply approved calibration recommendations through existing settings storage."""

    def __init__(self, settings_repository=None):
        self.settings_repository = settings_repository

    def apply_recommendations(self, recommendations, confirmed=False):
        recommendations = list(recommendations or [])
        if not confirmed:
            return CalibrationApplyResult(
                status="skipped",
                skipped=[self.skip_payload(item, "Confirmation required") for item in recommendations],
                message="Calibration recommendations were not applied because confirmation was not provided.",
            )

        applied = []
        failed = []
        skipped = []
        for recommendation in recommendations:
            update = self.update_from_recommendation(recommendation)
            if update is None:
                skipped.append(self.skip_payload(recommendation, "Unsupported recommendation"))
                continue
            key, proposed_value = update
            validation_error = self.validate_setting(key, proposed_value)
            if validation_error:
                failed.append(
                    {
                        "recommendation": self.recommendation_label(recommendation),
                        "key": key,
                        "value": proposed_value,
                        "reason": validation_error,
                    }
                )
                continue
            try:
                self.save_setting(key, proposed_value)
            except Exception as exc:
                failed.append(
                    {
                        "recommendation": self.recommendation_label(recommendation),
                        "key": key,
                        "value": proposed_value,
                        "reason": str(exc),
                    }
                )
                continue
            applied.append(
                {
                    "recommendation": self.recommendation_label(recommendation),
                    "key": key,
                    "value": proposed_value,
                }
            )

        status = "applied" if applied and not failed else ("failed" if failed else "skipped")
        if applied and failed:
            status = "partial"
        return CalibrationApplyResult(
            status=status,
            applied=applied,
            failed=failed,
            skipped=skipped,
            message=self.result_message(applied, failed, skipped),
        )

    def update_from_recommendation(self, recommendation):
        metric = str(value(recommendation, "related_metric") or value(recommendation, "category") or "")
        action = value(recommendation, "recommended_action")
        if action in (None, ""):
            action = value(recommendation, "recommended_value")

        if metric in THRESHOLD_KEYS:
            return THRESHOLD_KEYS[metric], numeric_value(action)

        metric_lower = metric.lower()
        title_lower = str(value(recommendation, "title") or "").lower()
        if "confidence" in metric_lower or "confidence" in title_lower:
            return "calibration.confidence_threshold", confidence_value(action)

        if "weight" in metric_lower or "weight" in title_lower:
            weights = weight_value(action, metric_lower)
            if weights is not None:
                return "calibration.scoring_weights", weights
        return None

    def validate_setting(self, key, proposed_value):
        if key == "calibration.confidence_threshold":
            if proposed_value not in CONFIDENCE_LEVELS:
                return "Confidence threshold must be LOW, MEDIUM, or HIGH."
            return None
        if key == "calibration.scoring_weights":
            if not isinstance(proposed_value, dict) or not proposed_value:
                return "Scoring weights must be a non-empty mapping."
            for name, raw in proposed_value.items():
                number = numeric_value(raw)
                if number is None or number < 0 or number > 1:
                    return f"Weight {name} must be between 0 and 1."
            return None
        if key in set(THRESHOLD_KEYS.values()):
            if proposed_value is None or proposed_value < 0 or proposed_value > 100:
                return "Score thresholds must be between 0 and 100."
            return None
        return "Unsupported setting."

    def save_setting(self, key, proposed_value):
        if self.settings_repository is None or not hasattr(self.settings_repository, "set_setting"):
            raise RuntimeError("Settings repository is unavailable.")
        return self.settings_repository.set_setting(key, proposed_value)

    @staticmethod
    def recommendation_label(recommendation):
        return str(
            value(recommendation, "title")
            or value(recommendation, "category")
            or value(recommendation, "related_metric")
            or "Calibration Recommendation"
        )

    @classmethod
    def skip_payload(cls, recommendation, reason):
        return {"recommendation": cls.recommendation_label(recommendation), "reason": reason}

    @staticmethod
    def result_message(applied, failed, skipped):
        return (
            f"Applied {len(applied)} recommendation(s), "
            f"failed {len(failed)}, skipped {len(skipped)}."
        )


def value(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def numeric_value(raw):
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw or "").strip()
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        return float(text)
    except ValueError:
        return None


def confidence_value(raw):
    text = str(raw or "").upper()
    for level in ("LOW", "MEDIUM", "HIGH"):
        if level in text:
            return level
    return text.strip()


def weight_value(raw, metric_name=""):
    if isinstance(raw, dict):
        return {str(key): numeric_value(value) for key, value in raw.items()}
    number = numeric_value(raw)
    if number is None:
        return None
    metric = metric_name.replace("calibration.", "").replace("_weight", "").replace("weight_", "")
    metric = metric.strip("._- ") or "overall"
    return {metric: number}
