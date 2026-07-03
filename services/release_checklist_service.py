from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from services.release_diagnostics_service import ReleaseDiagnosticsService


@dataclass(frozen=True)
class ReleaseChecklistItem:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class ReleaseChecklistReport:
    status: str
    items: list[ReleaseChecklistItem] = field(default_factory=list)
    summary: str = ""


class ReleaseChecklistService:
    def __init__(self, diagnostics_service=None, project_root=None):
        self.diagnostics_service = diagnostics_service or ReleaseDiagnosticsService()
        self.project_root = Path(project_root or ".")

    def run(self, include_build_checks=True, include_test_checks=True):
        items = []
        diagnostics = self.diagnostics_service.run()
        items.append(
            ReleaseChecklistItem(
                "release_diagnostics",
                diagnostics.status,
                f"Release diagnostics returned {diagnostics.status}",
            )
        )
        if include_test_checks:
            items.append(self.file_item("tests", self.project_root / "tests", "Test suite directory available"))
        if include_build_checks:
            items.append(
                self.file_item(
                    "pyinstaller_spec",
                    self.project_root / "InstitutionalBounceScreener.spec",
                    "PyInstaller spec available",
                )
            )
            items.append(
                self.file_item(
                    "build_script",
                    self.project_root / "scripts" / "build_release.ps1",
                    "Build script available",
                )
            )
        items.append(
            self.file_item(
                "release_docs",
                self.project_root / "docs" / "BUILD_AND_RELEASE.md",
                "Build and release documentation available",
            )
        )
        items.append(
            self.file_item(
                "release_checklist_docs",
                self.project_root / "docs" / "RELEASE_CHECKLIST.md",
                "Release checklist documentation available",
            )
        )
        status = self.overall_status(items)
        return ReleaseChecklistReport(
            status=status,
            items=items,
            summary=f"{status}: {sum(item.status == 'PASS' for item in items)}/{len(items)} release checks passing",
        )

    @staticmethod
    def file_item(name, path, message):
        exists = Path(path).exists()
        return ReleaseChecklistItem(
            name,
            "PASS" if exists else "FAIL",
            message if exists else f"Missing: {path}",
        )

    @staticmethod
    def overall_status(items):
        if any(item.status == "FAIL" for item in items):
            return "FAIL"
        if any(item.status == "WARNING" for item in items):
            return "WARNING"
        return "PASS"
