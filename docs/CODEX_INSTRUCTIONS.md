# Codex Instructions

These instructions apply to all work in Institutional Bounce Screener.

## Required Reading

Before editing, read the relevant project documents:

1. `docs/PROJECT_MANIFEST.md`
2. `docs/ARCHITECTURE.md`
3. `docs/ROADMAP.md`
4. The files directly affected by the task

Read `docs/DECISIONS.md` when a task touches architecture, persistence, scoring, or UI structure.

## Architecture Rules

Preserve the layered architecture:

```text
GUI
Controllers
Services
DatabaseManager
SQLite
```

Rules:

- No business logic in GUI files.
- No SQL outside `DatabaseManager`.
- No database access inside indicators, support calculators, bounce calculators, or score providers.
- No market downloads inside analytics calculators.
- Controllers coordinate; they do not calculate.
- Services own business workflows.
- `DatabaseManager` owns persistence.
- GUI displays data and forwards user actions.
- Keep `MainWindow` thin.
- Prefer reusable widgets in `ui/widgets/`.
- Preserve existing behavior unless the task explicitly changes it.

## Change Discipline

- Implement one feature or issue at a time.
- Modify only files required for the approved scope.
- Do not change scoring formulas unless explicitly requested.
- Do not change database schema unless explicitly requested.
- Do not redesign UI outside the approved UI scope.
- Do not modify unrelated files.
- Do not use `print()` in application code; use logging.
- Use parameterized SQL for all database writes and reads.
- Keep missing optional data safe; missing CSVs or metrics must not crash the app.

## Testing and Verification

Before completion of code changes, run:

```powershell
.venv\Scripts\python.exe -m compileall app.py main.py controllers services support bounce database ui analysis tests
.venv\Scripts\python.exe -m pytest
```

If a task only changes documentation, tests are not required unless documentation tooling exists.

## Reporting

Final responses must include:

- Files changed.
- Why each file changed.
- Verification commands run and results.
- Any known limitations or skipped checks.

If files were not changed, say so clearly.

## Git Hygiene

- One feature per commit.
- Never revert user changes unless explicitly asked.
- Do not use destructive git commands without explicit approval.
- Keep generated cache files out of commits.
