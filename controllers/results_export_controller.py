from __future__ import annotations

from pathlib import Path

from services.results_export_service import ResultsExportService


class ResultsExportController:
    """
    UI-safe wrapper for exporting ranked screening results.
    """

    def __init__(
        self,
        repository,
        export_service=None,
        output_dir=None,
    ):
        self.repository = repository
        self.export_service = export_service or ResultsExportService()
        self.output_dir = Path(output_dir or "exports/results")

    def export_candidates_csv(self, run_id=None):
        context = self.export_context(run_id)
        if not context["success"]:
            return context
        return self.export_service.export_ranked_candidates_csv(
            context["candidates"],
            self.output_dir,
            self.filename("ranked_candidates", context["run_id"]),
        )

    def export_candidates_json(self, run_id=None):
        context = self.export_context(run_id)
        if not context["success"]:
            return context
        return self.export_service.export_ranked_candidates_json(
            context["candidates"],
            self.output_dir,
            self.filename("ranked_candidates", context["run_id"]),
        )

    def export_full_run_package_json(self, run_id=None):
        context = self.export_context(run_id)
        if not context["success"]:
            return context
        return self.export_service.export_full_run_package(
            context["run"],
            context["candidates"],
            self.output_dir,
            self.filename("screening_run_package", context["run_id"]),
        )

    def export_context(self, run_id=None):
        if self.repository is None:
            return self.result(False, "No screening repository is available.")

        selected_run_id = str(run_id).strip() if run_id not in (None, "") else None
        run = self.fetch_run(selected_run_id)
        resolved_run_id = self.value(run, "run_id") or selected_run_id

        if resolved_run_id in (None, ""):
            return self.result(False, "No screening run available.")

        candidates = self.fetch_candidates(resolved_run_id)
        if not candidates:
            return self.result(False, "No ranked candidates available.")

        return {
            "success": True,
            "message": "Export context loaded.",
            "run": run or {"run_id": resolved_run_id},
            "run_id": resolved_run_id,
            "candidates": candidates,
            "path": None,
            "count": len(candidates),
        }

    def fetch_run(self, run_id=None):
        if run_id and hasattr(self.repository, "fetch_screening_run"):
            return self.repository.fetch_screening_run(run_id)
        if run_id:
            return {"run_id": run_id}
        if hasattr(self.repository, "fetch_latest_screening_run"):
            return self.repository.fetch_latest_screening_run()
        if hasattr(self.repository, "fetch_screening_run_history"):
            runs = self.repository.fetch_screening_run_history(limit=1) or []
            return runs[0] if runs else None
        return None

    def fetch_candidates(self, run_id):
        if hasattr(self.repository, "fetch_ranked_candidates"):
            return list(self.repository.fetch_ranked_candidates(run_id) or [])
        if hasattr(self.repository, "fetch_latest_ranked_candidates"):
            return list(self.repository.fetch_latest_ranked_candidates() or [])
        return []

    @staticmethod
    def filename(prefix, run_id):
        return f"{prefix}_{run_id or 'latest'}"

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def result(success, message, path=None, count=None):
        return {
            "success": success,
            "message": message,
            "path": str(path) if path is not None else None,
            "count": count,
        }
