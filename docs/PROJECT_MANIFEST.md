# Project Manifest

## Project

Institutional Bounce Screener is a desktop application for identifying high-probability institutional bounce opportunities in U.S. stocks.

The application combines market data, technical indicators, institutional support analysis, ranking, and future backtesting into a professional screening workflow.

## Technology Stack

- Python 3.13
- PySide6
- pandas
- yfinance
- SQLite

## Architectural Contract

The project follows a strict layered architecture:

```text
GUI
Controllers
Services
DatabaseManager
SQLite
```

Responsibilities must remain separated:

- GUI builds screens, receives user actions, and displays results.
- Controllers connect GUI actions to service calls.
- Services contain business logic and workflow orchestration.
- Indicators perform calculations only.
- DatabaseManager performs persistence only.
- SQLite stores application data.

## Non-Negotiable Rules

- Do not place business logic in the GUI.
- Do not place database writes or reads inside indicators.
- Do not download market data inside indicators.
- Do not perform calculations inside controllers.
- Do not use `print()` in application code.
- Use logging for operational messages.
- Preserve existing functionality unless a task explicitly requires a change.
- Keep the application compiling after every completed task.
- Do not modify unrelated files.
- Do not modify more than one architectural layer unless the task explicitly requires it.

## Current Release Target

Release: v0.9.0

Goal: release the Indicator Engine Foundation.

Required scope:

- BaseIndicator foundation.
- SMA20, SMA50, and SMA200 indicators.
- IndicatorService workflow.
- DatabaseManager support for indicator persistence.
- Calculate Indicators workflow.
- Tests for indicator and service behavior.

## Current Application Areas

- `app.py`: primary application entry point.
- `ui/`: PySide6 desktop interface.
- `controllers/`: UI-to-service coordination.
- `services/`: business workflows.
- `market/`: universe loading and market data downloading helpers.
- `database/`: SQLite schema and persistence manager.
- `indicators/`: technical indicator calculations.
- `data/`: local market data, universe files, and SQLite database.
- `docs/`: project instructions and task planning.

## Development Guidance

Before changing code:

1. Read this manifest.
2. Read `docs/CODEX_INSTRUCTIONS.md`.
3. Read `docs/TASK.md`.
4. Inspect the affected files.
5. Modify only the files required for the task.
6. Run an appropriate compile or test check.
7. Explain every modified file.
