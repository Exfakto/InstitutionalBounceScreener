from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path


PRIORITY_BLOCKER = "blocker"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"
PRIORITIES = [PRIORITY_BLOCKER, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW]

DEFAULT_REQUIRED_PATHS = [
    "README.md",
    "docs/PROJECT_MANIFEST.md",
    "docs/rc1_release_freeze_checklist.md",
    "docs/rc1_full_regression_checklist.md",
    "docs/rc1_clean_windows_install_validation.md",
    "docs/final_repository_review.md",
    "docs/release_candidate_punch_list.md",
    "scripts/run_rc1_regression.py",
    "scripts/repository_review.py",
    "scripts/verify_packaging.py",
    "scripts/verify_clean_install_readiness.py",
    "tests/test_rc1_regression_runner.py",
    "tests/test_clean_install_readiness.py",
]
REVIEWED_SOURCE_DIRS = [
    "services",
    "controllers",
    "ui/widgets",
    "scripts",
]
IGNORED_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "build",
    "dist",
}
TODO_MARKERS = ["TODO", "FIXME"]
RUNTIME_ARTIFACT_SUFFIXES = [".pyc", ".pyo", ".log", ".tmp"]


@dataclass(frozen=True)
class ReviewIssue:
    priority: str
    category: str
    path: str
    message: str
    recommendation: str


@dataclass(frozen=True)
class RepositoryReviewResult:
    success: bool
    issues: list[ReviewIssue] = field(default_factory=list)
    checked_paths: list[str] = field(default_factory=list)

    @property
    def blockers(self):
        return [issue for issue in self.issues if issue.priority == PRIORITY_BLOCKER]

    @property
    def high_priority(self):
        return [issue for issue in self.issues if issue.priority == PRIORITY_HIGH]


def review_repository(project_root=None):
    root = Path(project_root or Path(__file__).resolve().parents[1])
    issues = []
    checked = []
    issues.extend(find_missing_required_files(root, DEFAULT_REQUIRED_PATHS, checked))
    issues.extend(find_todo_comments(root, checked))
    issues.extend(find_duplicate_modules(root, checked))
    issues.extend(find_runtime_artifacts(root, checked))
    issues.extend(find_missing_manifest_entries(root, checked))
    issues.extend(find_missing_tests(root, checked))
    issues.extend(find_stale_document_references(root, checked))
    return RepositoryReviewResult(
        success=not any(issue.priority == PRIORITY_BLOCKER for issue in issues),
        issues=sorted_issues(issues),
        checked_paths=checked,
    )


def find_missing_required_files(root, required_paths, checked):
    issues = []
    for relative in required_paths:
        checked.append(relative)
        if not (root / relative).exists():
            issues.append(
                ReviewIssue(
                    priority=PRIORITY_BLOCKER,
                    category="missing_file",
                    path=relative,
                    message=f"Required release file is missing: {relative}",
                    recommendation="Restore the file or update the RC1 release checklist if it is intentionally removed.",
                )
            )
    return issues


def find_todo_comments(root, checked):
    issues = []
    for path in iter_text_files(root):
        if path.suffix.lower() not in {".py", ".ps1"}:
            continue
        relative = as_relative(root, path)
        checked.append(relative)
        text = safe_read(path)
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if path.suffix.lower() == ".py" and not stripped.startswith("#"):
                continue
            if path.suffix.lower() == ".ps1" and not stripped.startswith("#"):
                continue
            upper = stripped.upper()
            if any(marker in upper for marker in TODO_MARKERS):
                issues.append(
                    ReviewIssue(
                        priority=PRIORITY_LOW,
                        category="todo_fixme",
                        path=f"{relative}:{line_number}",
                        message="TODO/FIXME marker found.",
                        recommendation="Resolve before final release or document why the marker is acceptable.",
                    )
                )
    return issues


def find_duplicate_modules(root, checked):
    issues = []
    module_paths = []
    for folder in ["services", "controllers", "ui/widgets"]:
        base = root / folder
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if ignored(path):
                continue
            if path.name == "__init__.py":
                continue
            checked.append(as_relative(root, path))
            module_paths.append(path)

    by_stem = {}
    for path in module_paths:
        by_stem.setdefault(path.stem, []).append(as_relative(root, path))

    for stem, paths in sorted(by_stem.items()):
        if len(paths) > 1:
            issues.append(
                ReviewIssue(
                    priority=PRIORITY_MEDIUM,
                    category="duplicate_module_name",
                    path=", ".join(paths),
                    message=f"Duplicate module stem found: {stem}",
                    recommendation="Confirm the modules are intentionally distinct or rename for clarity.",
                )
            )
    return issues


def find_runtime_artifacts(root, checked):
    issues = []
    for path in root.rglob("*"):
        if ignored(path) or path.is_dir():
            continue
        relative = as_relative(root, path)
        if path.suffix.lower() in RUNTIME_ARTIFACT_SUFFIXES:
            checked.append(relative)
            issues.append(
                ReviewIssue(
                    priority=PRIORITY_MEDIUM,
                    category="runtime_artifact",
                    path=relative,
                    message="Runtime artifact found in repository tree.",
                    recommendation="Remove from release bundle or add a documented packaging exclusion.",
                )
            )
    return issues


def find_missing_manifest_entries(root, checked):
    manifest_path = root / "docs" / "PROJECT_MANIFEST.md"
    if not manifest_path.exists():
        return []
    checked.append("docs/PROJECT_MANIFEST.md")
    manifest = manifest_path.read_text(encoding="utf-8")
    issues = []
    for folder in REVIEWED_SOURCE_DIRS:
        base = root / folder
        if not base.exists():
            continue
        for path in base.glob("*.py"):
            if path.name == "__init__.py":
                continue
            relative = as_relative(root, path)
            checked.append(relative)
            if path.name not in manifest and relative not in manifest:
                issues.append(
                    ReviewIssue(
                        priority=PRIORITY_LOW,
                        category="manifest_coverage",
                        path=relative,
                        message="Major module is not explicitly represented in PROJECT_MANIFEST.md.",
                        recommendation="Add the module or subsystem to the manifest if it is release-critical.",
                    )
                )
    return issues


def find_missing_tests(root, checked):
    issues = []
    tests_dir = root / "tests"
    test_names = {path.name for path in tests_dir.glob("test_*.py")} if tests_dir.exists() else set()
    for folder in ["services", "controllers"]:
        base = root / folder
        if not base.exists():
            continue
        for path in base.glob("*.py"):
            if path.name == "__init__.py":
                continue
            relative = as_relative(root, path)
            checked.append(relative)
            expected = f"test_{path.stem}.py"
            if expected not in test_names:
                issues.append(
                    ReviewIssue(
                        priority=PRIORITY_MEDIUM,
                        category="missing_test",
                        path=relative,
                        message=f"No direct test file named {expected}.",
                        recommendation="Add direct tests or document coverage through integration tests.",
                    )
                )
    return issues


def find_stale_document_references(root, checked):
    issues = []
    for path in (root / "docs").glob("*.md") if (root / "docs").exists() else []:
        relative = as_relative(root, path)
        checked.append(relative)
        text = safe_read(path)
        for token in extract_backtick_paths(text):
            if token.startswith(("http://", "https://", ".venv")):
                continue
            if any(character.isspace() for character in token):
                continue
            if "/" not in token and "\\" not in token:
                continue
            normalized = token.replace("\\", "/").strip()
            if normalized.endswith("/"):
                continue
            if not (root / normalized).exists():
                issues.append(
                    ReviewIssue(
                        priority=PRIORITY_LOW,
                        category="stale_doc_reference",
                        path=relative,
                        message=f"Document references missing path: {token}",
                        recommendation="Update the documentation reference or restore the referenced file.",
                    )
                )
    return issues


def extract_backtick_paths(text):
    parts = text.split("`")
    return [parts[index].strip() for index in range(1, len(parts), 2)]


def sorted_issues(issues):
    priority_rank = {priority: index for index, priority in enumerate(PRIORITIES)}
    return sorted(
        issues,
        key=lambda issue: (priority_rank.get(issue.priority, 99), issue.category, issue.path),
    )


def format_punch_list(result):
    lines = [
        "Final Repository Review",
        f"Status: {'PASS' if result.success else 'FAIL'}",
        f"Checked paths: {len(set(result.checked_paths))}",
    ]
    for priority in PRIORITIES:
        matching = [issue for issue in result.issues if issue.priority == priority]
        lines.append("")
        lines.append(f"{priority.title()} Priority")
        if not matching:
            lines.append("- None")
            continue
        for issue in matching:
            lines.append(f"- [{issue.category}] {issue.path}: {issue.message}")
            lines.append(f"  Recommendation: {issue.recommendation}")
    return "\n".join(lines)


def iter_text_files(root):
    for path in root.rglob("*"):
        if ignored(path) or not path.is_file():
            continue
        if path.suffix.lower() in {".py", ".md", ".txt", ".ps1", ".json", ".csv"}:
            yield path


def ignored(path):
    return any(part in IGNORED_PARTS for part in path.parts)


def safe_read(path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def as_relative(root, path):
    return path.relative_to(root).as_posix()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the final RC1 repository review.")
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root to review. Defaults to the repository root.",
    )
    args = parser.parse_args(argv)
    result = review_repository(args.project_root)
    print(format_punch_list(result))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
