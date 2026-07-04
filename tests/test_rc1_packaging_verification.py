from pathlib import Path

from scripts.verify_packaging import main, verify_packaging


REQUIRED_FILES = [
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


def create_packaging_fixture(root):
    for relative in REQUIRED_FILES:
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


def test_rc1_packaging_verification_success(tmp_path):
    create_packaging_fixture(tmp_path)

    result = verify_packaging(tmp_path)

    assert result.success is True
    assert result.missing_paths == []
    assert result.missing_metadata == []
    assert result.warnings == []
    assert result.build_output_path == "dist/"


def test_rc1_packaging_verification_detects_missing_required_file(tmp_path):
    create_packaging_fixture(tmp_path)
    (tmp_path / "app_entry.py").unlink()

    result = verify_packaging(tmp_path)

    assert result.success is False
    assert "app_entry.py" in result.missing_paths


def test_rc1_packaging_verification_detects_missing_metadata(tmp_path):
    create_packaging_fixture(tmp_path)
    (tmp_path / "config" / "app_metadata.py").write_text(
        'APPLICATION_NAME = "Institutional Bounce Screener"\n',
        encoding="utf-8",
    )

    result = verify_packaging(tmp_path)

    assert result.success is False
    assert "VERSION" in result.missing_metadata
    assert "SCHEMA_VERSION" in result.missing_metadata


def test_rc1_packaging_verification_cli_exit_codes(tmp_path, capsys):
    create_packaging_fixture(tmp_path)

    assert main(["--project-root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "Status: PASS" in output

    (tmp_path / "main.py").unlink()
    assert main(["--project-root", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "Status: FAIL" in output
    assert "main.py" in output


def test_real_repository_packaging_verification_is_offline_ready():
    root = Path(__file__).resolve().parents[1]

    result = verify_packaging(root)

    assert result.success is True
    assert result.missing_paths == []
    assert result.missing_metadata == []
