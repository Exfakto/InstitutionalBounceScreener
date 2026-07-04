from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify_packaging import verify_packaging


REQUIRED_DOCUMENTS = [
    "docs/rc1_clean_windows_install_validation.md",
    "docs/rc1_release_freeze_checklist.md",
    "docs/rc1_packaging_verification.md",
]
REQUIRED_CLEAN_INSTALL_PHRASES = [
    "Packaged App Dependencies",
    "Expected Runtime Folders",
    "First-Launch Behavior",
    "Logs, Config, Database, and Export Paths",
    "Clean Windows Validation Steps",
    "No separate Python installation should be required",
    "logs/",
    "config/",
    "data/institutional_bounce.db",
    "exports/results/",
    "data/backups/",
    "ResourcePathService",
    "does not require live market data access or API keys",
]
REQUIRED_PACKAGING_PHRASES = [
    "dist/",
    "config/app_metadata.py",
    "resources/README.md",
    "data/market_universe_seed.csv",
    "Offline Guarantee",
]
REQUIRED_FREEZE_PHRASES = [
    "Packaging validation",
    "Documentation Updated for v2.0 RC1",
    "docs/rc1_clean_windows_install_validation.md",
]


@dataclass(frozen=True)
class CleanInstallReadinessResult:
    success: bool
    checked_documents: list[str] = field(default_factory=list)
    missing_documents: list[str] = field(default_factory=list)
    missing_phrases: dict[str, list[str]] = field(default_factory=dict)
    packaging_success: bool = False
    warnings: list[str] = field(default_factory=list)


def verify_clean_install_readiness(project_root=None):
    root = Path(project_root or PROJECT_ROOT)
    checked = []
    missing_docs = []
    missing_phrases = {}

    for relative in REQUIRED_DOCUMENTS:
        checked.append(relative)
        path = root / relative
        if not path.exists():
            missing_docs.append(relative)

    check_phrases(
        root,
        "docs/rc1_clean_windows_install_validation.md",
        REQUIRED_CLEAN_INSTALL_PHRASES,
        missing_phrases,
    )
    check_phrases(
        root,
        "docs/rc1_packaging_verification.md",
        REQUIRED_PACKAGING_PHRASES,
        missing_phrases,
    )
    check_phrases(
        root,
        "docs/rc1_release_freeze_checklist.md",
        REQUIRED_FREEZE_PHRASES,
        missing_phrases,
    )

    packaging = verify_packaging(root)
    warnings = list(packaging.warnings)
    if packaging.missing_paths:
        missing_phrases.setdefault("packaging_prerequisites", []).extend(
            f"missing path: {path}" for path in packaging.missing_paths
        )
    if packaging.missing_metadata:
        missing_phrases.setdefault("packaging_prerequisites", []).extend(
            f"missing metadata: {name}" for name in packaging.missing_metadata
        )

    return CleanInstallReadinessResult(
        success=not missing_docs and not missing_phrases and packaging.success,
        checked_documents=checked,
        missing_documents=missing_docs,
        missing_phrases=missing_phrases,
        packaging_success=packaging.success,
        warnings=warnings,
    )


def check_phrases(root, relative, phrases, missing_phrases):
    path = root / relative
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    missing = [phrase for phrase in phrases if phrase not in text]
    if missing:
        missing_phrases[relative] = missing


def format_result(result):
    lines = [
        "RC1 Clean Windows Install Readiness",
        f"Status: {'PASS' if result.success else 'FAIL'}",
        f"Packaging verification: {'PASS' if result.packaging_success else 'FAIL'}",
        f"Checked documents: {len(result.checked_documents)}",
    ]
    if result.missing_documents:
        lines.append("Missing documents:")
        lines.extend(f"- {path}" for path in result.missing_documents)
    if result.missing_phrases:
        lines.append("Missing required documentation:")
        for document, phrases in result.missing_phrases.items():
            lines.append(f"- {document}")
            lines.extend(f"  - {phrase}" for phrase in phrases)
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in result.warnings)
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify RC1 clean Windows install readiness documentation."
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root to verify. Defaults to the repository root.",
    )
    args = parser.parse_args(argv)
    result = verify_clean_install_readiness(args.project_root)
    print(format_result(result))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
