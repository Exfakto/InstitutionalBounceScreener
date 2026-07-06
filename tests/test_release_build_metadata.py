from pathlib import Path

from config.app_metadata import (
    APPLICATION_NAME,
    BUILD_DATE,
    BUILD_TIMESTAMP,
    RELEASE_CHANNEL,
    SCHEMA_VERSION,
    VERSION,
)
from services.release_metadata_service import ReleaseMetadataService


def test_release_build_metadata_constants_and_service():
    metadata = ReleaseMetadataService().metadata()
    summary = ReleaseMetadataService().build_environment_summary()

    assert APPLICATION_NAME == "Institutional Bounce Platform"
    assert VERSION == "v2.2.0 RC"
    assert BUILD_DATE
    assert BUILD_TIMESTAMP
    assert RELEASE_CHANNEL in {"dev", "beta", "stable", "rc"}
    assert SCHEMA_VERSION
    assert metadata.version == VERSION
    assert summary["release_channel"] == RELEASE_CHANNEL


def test_release_build_scripts_docs_and_entrypoint_exist():
    assert Path("app_entry.py").exists()
    assert Path("InstitutionalBounceScreener.spec").exists()
    assert Path("scripts/build_release.ps1").exists()
    assert Path("scripts/run_release_checks.ps1").exists()
    assert Path("docs/BUILD_AND_RELEASE.md").exists()
    assert Path("docs/RELEASE_CHECKLIST.md").exists()

    assert "PyInstaller" in Path("docs/BUILD_AND_RELEASE.md").read_text(encoding="utf-8")
    assert "Release Checklist" in Path("docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
