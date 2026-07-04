from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path


REQUIRED_ENTRY_POINTS = [
    "app.py",
    "main.py",
    "app_entry.py",
]
REQUIRED_CONFIG_FILES = [
    "config/app_metadata.py",
    "config/logging_config.py",
    "config/providers.json",
    "config/scoring.json",
    "config/settings.py",
]
REQUIRED_RESOURCE_PATHS = [
    "resources/README.md",
    "data/market_universe_template.csv",
    "data/market_universe_seed.csv",
]
REQUIRED_BUILD_FILES = [
    "InstitutionalBounceScreener.spec",
    "scripts/build_release.ps1",
    "scripts/run_release_checks.ps1",
    "docs/BUILD_AND_RELEASE.md",
]
REQUIRED_METADATA_NAMES = [
    "APPLICATION_NAME",
    "VERSION",
    "BUILD_DATE",
    "BUILD_TIMESTAMP",
    "RELEASE_CHANNEL",
    "SCHEMA_VERSION",
]


@dataclass(frozen=True)
class PackagingVerificationResult:
    success: bool
    checked_paths: list[str] = field(default_factory=list)
    missing_paths: list[str] = field(default_factory=list)
    metadata_present: list[str] = field(default_factory=list)
    missing_metadata: list[str] = field(default_factory=list)
    build_output_path: str = "dist/"
    warnings: list[str] = field(default_factory=list)


def verify_packaging(project_root=None):
    root = Path(project_root or Path(__file__).resolve().parents[1])
    required_paths = [
        *REQUIRED_ENTRY_POINTS,
        *REQUIRED_CONFIG_FILES,
        *REQUIRED_RESOURCE_PATHS,
        *REQUIRED_BUILD_FILES,
    ]
    checked = []
    missing = []
    for relative in required_paths:
        checked.append(relative)
        if not (root / relative).exists():
            missing.append(relative)

    metadata_present, missing_metadata = verify_metadata(root)
    warnings = []
    if not build_output_documented(root):
        warnings.append("Build output path dist/ is not documented in docs/BUILD_AND_RELEASE.md")

    return PackagingVerificationResult(
        success=not missing and not missing_metadata and not warnings,
        checked_paths=checked,
        missing_paths=missing,
        metadata_present=metadata_present,
        missing_metadata=missing_metadata,
        build_output_path="dist/",
        warnings=warnings,
    )


def verify_metadata(root):
    metadata_file = root / "config" / "app_metadata.py"
    if not metadata_file.exists():
        return [], list(REQUIRED_METADATA_NAMES)
    text = metadata_file.read_text(encoding="utf-8")
    present = [name for name in REQUIRED_METADATA_NAMES if f"{name} =" in text]
    missing = [name for name in REQUIRED_METADATA_NAMES if name not in present]
    return present, missing


def build_output_documented(root):
    path = root / "docs" / "BUILD_AND_RELEASE.md"
    if not path.exists():
        return False
    return "dist/" in path.read_text(encoding="utf-8")


def format_result(result):
    lines = [
        "RC1 Packaging Verification",
        f"Status: {'PASS' if result.success else 'FAIL'}",
        f"Build output: {result.build_output_path}",
        f"Checked paths: {len(result.checked_paths)}",
    ]
    if result.missing_paths:
        lines.append("Missing paths:")
        lines.extend(f"- {path}" for path in result.missing_paths)
    if result.missing_metadata:
        lines.append("Missing metadata:")
        lines.extend(f"- {name}" for name in result.missing_metadata)
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in result.warnings)
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify RC1 packaging prerequisites.")
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root to verify. Defaults to the repository root.",
    )
    args = parser.parse_args(argv)
    result = verify_packaging(args.project_root)
    print(format_result(result))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
