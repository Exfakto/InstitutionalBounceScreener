from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs" / "rc1_release_freeze_checklist.md"


def test_rc1_release_freeze_checklist_exists():
    assert CHECKLIST.exists()


def test_rc1_release_freeze_checklist_contains_required_sections():
    text = CHECKLIST.read_text(encoding="utf-8")

    required_sections = [
        "# RC1 Release Freeze Checklist",
        "## Feature Freeze Rules",
        "## Required RC1 Validation Steps",
        "## RC1 Smoke Tests",
        "## Architecture Audit",
        "## Production Readiness",
        "## Provider Validation",
        "## Full Universe Validation",
        "## Export Validation",
        "## Packaging Validation",
        "## Documentation Updated for v2.0 RC1",
        "## Critical Blockers",
        "## Freeze Decision",
    ]
    missing = [section for section in required_sections if section not in text]

    assert missing == []


def test_rc1_release_freeze_checklist_names_required_validation_gates():
    text = CHECKLIST.read_text(encoding="utf-8")

    required_phrases = [
        "No new application features after RC1 freeze.",
        "RC1 smoke tests",
        "Repository architecture audit",
        "Release Candidate Validation suite",
        "Production readiness dashboard",
        "Provider configuration validation",
        "Full universe validation",
        "Export validation",
        "Packaging validation",
        "No known critical blockers",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in text]

    assert missing == []


def test_rc1_release_freeze_checklist_is_referenced_by_release_docs():
    manifest = (ROOT / "docs" / "PROJECT_MANIFEST.md").read_text(encoding="utf-8")
    instructions = (ROOT / "docs" / "CODEX_INSTRUCTIONS.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    combined = "\n".join([manifest, instructions, readme])

    assert "docs/rc1_release_freeze_checklist.md" in combined
    assert "v2.0 RC1" in combined
