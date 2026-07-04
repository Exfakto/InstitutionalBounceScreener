from pathlib import Path

from scripts.verify_clean_install_readiness import (
    REQUIRED_CLEAN_INSTALL_PHRASES,
    REQUIRED_FREEZE_PHRASES,
    REQUIRED_PACKAGING_PHRASES,
    main,
    verify_clean_install_readiness,
)


REQUIRED_PACKAGING_FILES = [
    "app.py",
    "main.py",
    "app_entry.py",
    "config/app_metadata.py",
    "config/logging_config.py",
    "config/providers.json",
    "config/scoring.json",
    "config/settings.py",
    "resources/README.md",
    "data/market_universe_template.csv",
    "data/market_universe_seed.csv",
    "InstitutionalBounceScreener.spec",
    "scripts/build_release.ps1",
    "scripts/run_release_checks.ps1",
    "docs/BUILD_AND_RELEASE.md",
]


def create_clean_install_fixture(root):
    for relative in REQUIRED_PACKAGING_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "config/app_metadata.py":
            path.write_text(
                "\n".join(
                    [
                        'APPLICATION_NAME = "Institutional Bounce Screener"',
                        'VERSION = "2.0.0-rc1"',
                        'BUILD_DATE = "2026-07-04"',
                        'BUILD_TIMESTAMP = "2026-07-04T00:00:00Z"',
                        'RELEASE_CHANNEL = "rc"',
                        'SCHEMA_VERSION = "1"',
                    ]
                ),
                encoding="utf-8",
            )
        elif relative == "docs/BUILD_AND_RELEASE.md":
            path.write_text("Release artifacts are written to:\n\n`dist/`\n", encoding="utf-8")
        else:
            path.write_text("fixture\n", encoding="utf-8")

    write_doc(root, "docs/rc1_clean_windows_install_validation.md", REQUIRED_CLEAN_INSTALL_PHRASES)
    write_doc(root, "docs/rc1_packaging_verification.md", REQUIRED_PACKAGING_PHRASES)
    write_doc(root, "docs/rc1_release_freeze_checklist.md", REQUIRED_FREEZE_PHRASES)


def write_doc(root, relative, phrases):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(phrases), encoding="utf-8")


def test_clean_install_readiness_success(tmp_path):
    create_clean_install_fixture(tmp_path)

    result = verify_clean_install_readiness(tmp_path)

    assert result.success is True
    assert result.packaging_success is True
    assert result.missing_documents == []
    assert result.missing_phrases == {}


def test_clean_install_readiness_detects_missing_required_document(tmp_path):
    create_clean_install_fixture(tmp_path)
    (tmp_path / "docs" / "rc1_clean_windows_install_validation.md").unlink()

    result = verify_clean_install_readiness(tmp_path)

    assert result.success is False
    assert "docs/rc1_clean_windows_install_validation.md" in result.missing_documents


def test_clean_install_readiness_detects_missing_required_documentation_phrase(tmp_path):
    create_clean_install_fixture(tmp_path)
    (tmp_path / "docs" / "rc1_clean_windows_install_validation.md").write_text(
        "Packaged App Dependencies\nExpected Runtime Folders\n",
        encoding="utf-8",
    )

    result = verify_clean_install_readiness(tmp_path)

    missing = result.missing_phrases["docs/rc1_clean_windows_install_validation.md"]
    assert result.success is False
    assert "First-Launch Behavior" in missing
    assert "logs/" in missing


def test_clean_install_readiness_reports_missing_packaging_prerequisites(tmp_path):
    create_clean_install_fixture(tmp_path)
    (tmp_path / "config" / "providers.json").unlink()

    result = verify_clean_install_readiness(tmp_path)

    assert result.success is False
    assert "missing path: config/providers.json" in result.missing_phrases["packaging_prerequisites"]


def test_clean_install_readiness_cli_exit_codes(tmp_path, capsys):
    create_clean_install_fixture(tmp_path)

    assert main(["--project-root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "Status: PASS" in output

    (tmp_path / "docs" / "rc1_packaging_verification.md").unlink()
    assert main(["--project-root", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "Status: FAIL" in output
    assert "docs/rc1_packaging_verification.md" in output


def test_real_repository_clean_install_readiness_is_documented():
    root = Path(__file__).resolve().parents[1]

    result = verify_clean_install_readiness(root)

    assert result.success is True
    assert result.missing_documents == []
    assert result.missing_phrases == {}
