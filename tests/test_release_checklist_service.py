from pathlib import Path

from services.release_checklist_service import ReleaseChecklistService


class Diagnostics:
    def __init__(self, status="PASS"):
        self.status = status

    def run(self):
        return type("Report", (), {"status": self.status})()


def prepare_project(root, include_spec=True):
    (root / "tests").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "scripts" / "build_release.ps1").write_text("ok", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "BUILD_AND_RELEASE.md").write_text("ok", encoding="utf-8")
    (root / "docs" / "RELEASE_CHECKLIST.md").write_text("ok", encoding="utf-8")
    if include_spec:
        (root / "InstitutionalBounceScreener.spec").write_text("ok", encoding="utf-8")


def test_release_checklist_passes_when_required_assets_exist(tmp_path):
    prepare_project(tmp_path)

    report = ReleaseChecklistService(
        diagnostics_service=Diagnostics("PASS"),
        project_root=tmp_path,
    ).run()

    assert report.status == "PASS"
    assert "release checks passing" in report.summary
    assert all(item.status == "PASS" for item in report.items)


def test_release_checklist_fails_when_build_asset_missing(tmp_path):
    prepare_project(tmp_path, include_spec=False)

    report = ReleaseChecklistService(
        diagnostics_service=Diagnostics("PASS"),
        project_root=tmp_path,
    ).run()

    assert report.status == "FAIL"
    assert any(item.name == "pyinstaller_spec" and item.status == "FAIL" for item in report.items)


def test_release_checklist_can_skip_build_and_test_checks(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "BUILD_AND_RELEASE.md").write_text("ok", encoding="utf-8")
    (tmp_path / "docs" / "RELEASE_CHECKLIST.md").write_text("ok", encoding="utf-8")

    report = ReleaseChecklistService(
        diagnostics_service=Diagnostics("WARNING"),
        project_root=tmp_path,
    ).run(include_build_checks=False, include_test_checks=False)

    assert report.status == "WARNING"
    assert {item.name for item in report.items} == {
        "release_diagnostics",
        "release_docs",
        "release_checklist_docs",
    }
