from datetime import datetime


class DashboardController:
    """Builds a UI-ready dashboard snapshot from existing application state."""

    def __init__(
        self,
        market_controller=None,
        watchlist_controller=None,
        market_status_service=None,
        settings_service=None,
    ):
        self.market_controller = market_controller
        self.watchlist_controller = watchlist_controller
        self.market_status_service = market_status_service
        self.settings_service = settings_service

    def get_dashboard_data(
        self,
        candidates=None,
        last_refresh=None,
        recent_research=None,
        backtesting_snapshot=None,
    ):
        candidate_list = list(candidates or [])
        warnings = []

        market_summary = self.market_summary(last_refresh=last_refresh, warnings=warnings)
        opportunity_summary = self.opportunity_summary(candidate_list)
        best_opportunities = self.best_opportunities(candidate_list)
        institutional_activity = self.institutional_activity(candidate_list)
        watchlist_summary = self.watchlist_summary(warnings=warnings)

        return {
            "market_summary": market_summary,
            "opportunity_summary": opportunity_summary,
            "best_opportunities": best_opportunities,
            "institutional_activity": institutional_activity,
            "watchlist_summary": watchlist_summary,
            "recent_research": list(recent_research or []),
            "backtesting_snapshot": dict(backtesting_snapshot or {}),
            "warnings": warnings,
        }

    def market_summary(self, last_refresh=None, warnings=None):
        status = self.safe_market_status(warnings)
        provider = self.safe_active_provider(warnings)
        database_status = self.safe_database_status(warnings)

        return {
            "market_status": status,
            "active_provider": provider,
            "last_refresh": self.format_datetime(last_refresh),
            "database_status": database_status,
        }

    def opportunity_summary(self, candidates):
        scores = [self.candidate_score(candidate) for candidate in candidates]
        scores = [score for score in scores if score is not None]
        average_score = sum(scores) / len(scores) if scores else None

        return {
            "candidates_screened": len(candidates),
            "high_conviction": sum(
                1 for candidate in candidates if self.is_high_conviction(candidate)
            ),
            "watch_candidates": sum(
                1 for candidate in candidates if self.is_watch_candidate(candidate)
            ),
            "average_opportunity_score": average_score,
        }

    def best_opportunities(self, candidates, limit=5):
        ranked = sorted(
            candidates,
            key=lambda candidate: self.candidate_score(candidate) or 0.0,
            reverse=True,
        )

        return [self.opportunity_row(candidate) for candidate in ranked[:limit]]

    def institutional_activity(self, candidates, limit=5):
        rows = []
        for candidate in candidates:
            row = self.institutional_row(candidate)
            values = [
                row.get("institutional_score"),
                row.get("ownership_trend"),
                row.get("insider_activity"),
                row.get("thirteen_f_status"),
            ]
            if any(value not in (None, "", "--") for value in values):
                rows.append(row)
        rows = sorted(
            rows,
            key=lambda row: row.get("institutional_score") or 0.0,
            reverse=True,
        )
        return rows[:limit]

    def watchlist_summary(self, warnings=None):
        if self.watchlist_controller is None or not hasattr(
            self.watchlist_controller, "get_watchlist_intelligence"
        ):
            return {}

        try:
            intelligence = self.watchlist_controller.get_watchlist_intelligence()
        except Exception as exc:
            if warnings is not None:
                warnings.append(f"Watchlist intelligence unavailable: {exc}")
            return {}

        return self.to_plain_dict(intelligence)

    def opportunity_row(self, candidate):
        metrics = self.object_value(candidate, "metrics") or {}
        return {
            "ticker": self.object_value(candidate, "ticker"),
            "company": self.first_existing(
                self.object_value(candidate, "company_name"),
                self.object_value(candidate, "company"),
                self.object_value(candidate, "name"),
            ),
            "opportunity_score": self.candidate_score(candidate),
            "confidence": self.first_existing(
                self.object_value(self.object_value(candidate, "trade_thesis"), "confidence"),
                self.object_value(metrics, "confidence"),
                self.object_value(candidate, "confidence"),
            ),
            "risk_reward": self.first_existing(
                self.object_value(metrics, "risk_reward"),
                self.object_value(candidate, "risk_reward"),
            ),
        }

    def institutional_row(self, candidate):
        metrics = self.object_value(candidate, "metrics") or {}
        score_map = self.object_value(candidate, "score_map") or {}
        return {
            "ticker": self.object_value(candidate, "ticker"),
            "institutional_score": self.number_value(
                self.first_existing(
                    self.object_value(score_map, "institutional_score"),
                    self.object_value(candidate, "institutional_score"),
                )
            ),
            "ownership_trend": self.first_existing(
                self.object_value(metrics, "ownership_trend"),
                self.object_value(metrics, "institutional_ownership_trend"),
                self.object_value(candidate, "ownership_trend"),
            ),
            "insider_activity": self.first_existing(
                self.object_value(metrics, "insider_activity"),
                self.object_value(candidate, "insider_activity"),
            ),
            "thirteen_f_status": self.first_existing(
                self.object_value(metrics, "thirteen_f_status"),
                self.object_value(metrics, "13f_status"),
                self.object_value(candidate, "thirteen_f_status"),
                self.object_value(candidate, "13f_status"),
            ),
        }

    def candidate_score(self, candidate):
        opportunity = self.object_value(candidate, "opportunity_rating")
        return self.number_value(
            self.first_existing(
                self.object_value(opportunity, "rating_score"),
                self.object_value(candidate, "primary_score_value"),
                self.object_value(candidate, "composite_score"),
            )
        )

    def is_high_conviction(self, candidate):
        label = str(
            self.object_value(self.object_value(candidate, "opportunity_rating"), "rating_label")
            or ""
        ).lower()
        score = self.candidate_score(candidate) or 0.0
        return "high" in label or "conviction" in label or score >= 85.0

    def is_watch_candidate(self, candidate):
        label = str(
            self.object_value(self.object_value(candidate, "opportunity_rating"), "rating_label")
            or ""
        ).lower()
        score = self.candidate_score(candidate)
        if "watch" in label:
            return True
        return score is not None and 70.0 <= score < 85.0

    def safe_market_status(self, warnings=None):
        if self.market_status_service is None:
            return None
        try:
            status = self.market_status_service.get_status()
            return self.object_value(status, "status")
        except Exception as exc:
            if warnings is not None:
                warnings.append(f"Market status unavailable: {exc}")
            return None

    def safe_active_provider(self, warnings=None):
        if self.settings_service is None:
            return None
        try:
            provider_status = self.settings_service.provider_status()
        except Exception as exc:
            if warnings is not None:
                warnings.append(f"Provider status unavailable: {exc}")
            return None

        if isinstance(provider_status, dict):
            return provider_status.get("current_provider")
        return None

    def safe_database_status(self, warnings=None):
        if self.market_controller is None or not hasattr(
            self.market_controller, "get_statistics"
        ):
            return None
        try:
            stats = self.market_controller.get_statistics()
        except Exception as exc:
            if warnings is not None:
                warnings.append(f"Database status unavailable: {exc}")
            return "Unavailable"
        if isinstance(stats, dict):
            return "Available"
        return None

    @staticmethod
    def format_datetime(value):
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value)

    @classmethod
    def number_value(cls, value):
        if hasattr(value, "value"):
            value = value.value
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def object_value(source, name):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(name)
        return getattr(source, name, None)

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def to_plain_dict(value):
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "__dict__"):
            return {
                key: item
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        return {}
