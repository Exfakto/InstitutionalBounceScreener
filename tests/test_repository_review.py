from pathlib import Path

from scripts.repository_review import (
    DEFAULT_REQUIRED_PATHS,
    PRIORITY_BLOCKER,
    PRIORITY_LOW,
    format_punch_list,
    main,
    review_repository,
)


def create_review_fixture(root):
    for relative in DEFAULT_REQUIRED_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    (root / "docs" / "PROJECT_MANIFEST.md").write_text(
        "\n".join(
            [
                "# Project Manifest",
                "services/reviewed_service.py",
                "controllers/reviewed_controller.py",
                "ui/widgets/reviewed_widget.py",
                "scripts/repository_review.py",
            ]
        ),
        encoding="utf-8",
    )
    for relative in [
        "services/reviewed_service.py",
        "controllers/reviewed_controller.py",
        "ui/widgets/reviewed_widget.py",
    ]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("VALUE = 1\n", encoding="utf-8")
    for relative in [
        "tests/test_reviewed_service.py",
        "tests/test_reviewed_controller.py",
    ]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")


def categories(result):
    return [issue.category for issue in result.issues]


def test_repository_review_output_for_complete_fixture(tmp_path):
    create_review_fixture(tmp_path)

    result = review_repository(tmp_path)
    output = format_punch_list(result)

    assert result.success is True
    assert "Final Repository Review" in output
    assert "Blocker Priority" in output
    assert "High Priority" in output
    assert "Medium Priority" in output
    assert "Low Priority" in output


def test_repository_review_detects_missing_required_file(tmp_path):
    create_review_fixture(tmp_path)
    (tmp_path / "scripts" / "run_rc1_regression.py").unlink()

    result = review_repository(tmp_path)

    assert result.success is False
    assert any(
        issue.priority == PRIORITY_BLOCKER
        and issue.category == "missing_file"
        and issue.path == "scripts/run_rc1_regression.py"
        for issue in result.issues
    )


def test_repository_review_detects_todo_fixme_source_comments(tmp_path):
    create_review_fixture(tmp_path)
    (tmp_path / "services" / "reviewed_service.py").write_text(
        "# TODO: tighten this before final release\nVALUE = 1\n",
        encoding="utf-8",
    )

    result = review_repository(tmp_path)

    assert "todo_fixme" in categories(result)
    issue = [issue for issue in result.issues if issue.category == "todo_fixme"][0]
    assert issue.priority == PRIORITY_LOW
    assert issue.path == "services/reviewed_service.py:1"


def test_repository_review_detects_missing_test_and_manifest_entry(tmp_path):
    create_review_fixture(tmp_path)
    (tmp_path / "services" / "uncovered_service.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    result = review_repository(tmp_path)

    assert any(
        issue.category == "missing_test"
        and issue.path == "services/uncovered_service.py"
        for issue in result.issues
    )
    assert any(
        issue.category == "manifest_coverage"
        and issue.path == "services/uncovered_service.py"
        for issue in result.issues
    )


def test_repository_review_detects_stale_document_reference(tmp_path):
    create_review_fixture(tmp_path)
    (tmp_path / "docs" / "stale.md").write_text(
        "This references `docs/missing_file.md`.\n",
        encoding="utf-8",
    )

    result = review_repository(tmp_path)

    assert any(
        issue.category == "stale_doc_reference"
        and issue.path == "docs/stale.md"
        for issue in result.issues
    )


def test_repository_review_cli_exit_codes(tmp_path, capsys):
    create_review_fixture(tmp_path)

    assert main(["--project-root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "Status: PASS" in output

    (tmp_path / "README.md").unlink()
    assert main(["--project-root", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "Status: FAIL" in output
    assert "README.md" in output


def test_real_repository_review_docs_are_linked():
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    review_doc = (root / "docs" / "final_repository_review.md").read_text(
        encoding="utf-8"
    )
    punch_list = (root / "docs" / "release_candidate_punch_list.md").read_text(
        encoding="utf-8"
    )

    assert "scripts/repository_review.py" in readme
    assert "docs/final_repository_review.md" in readme
    assert "Blocker" in review_doc
    assert "TODO/FIXME" in review_doc
    assert "Blocker Priority" in punch_list
    assert "High Priority" in punch_list
