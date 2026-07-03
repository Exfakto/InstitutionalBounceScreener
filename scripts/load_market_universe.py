from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.manager import DatabaseManager
from market.market_universe_importer import MarketUniverseImporter


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a market universe CSV into the local SQLite database."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        help="Path to the market universe CSV file.",
    )
    parser.add_argument(
        "--database-path",
        help="Optional SQLite database path. Defaults to the project database.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        csv_path=args.csv_path,
        database_path=args.database_path,
    )


def run(
    csv_path: str | Path | None = None,
    database_path: str | Path | None = None,
    importer_factory=None,
    output=print,
) -> int:
    if not csv_path:
        output("CSV path is required.")
        return 2

    path = Path(csv_path)

    if not path.exists() or not path.is_file():
        output(f"CSV file not found: {path}")
        return 2

    db = None

    try:
        if importer_factory is not None:
            importer = importer_factory(path)
        else:
            db = DatabaseManager(database_path=database_path)
            importer = MarketUniverseImporter(path, db=db)

        summary = importer.import_csv()
    except Exception as exc:
        output(f"Unable to import market universe: {exc}")
        return 1
    finally:
        if db is not None:
            db.close()

    output(format_summary(summary))

    if summary.get("errors") and not summary.get("records_imported", 0):
        return 1

    return 0


def format_summary(summary: dict) -> str:
    errors = summary.get("errors") or []
    lines = [
        "Market Universe Import Summary",
        f"Total rows read: {summary.get('total_rows_read', 0)}",
        f"Records imported: {summary.get('records_imported', 0)}",
        f"Records skipped: {summary.get('records_skipped', 0)}",
        f"Errors encountered: {len(errors)}",
    ]

    for error in errors:
        lines.append(f"- {error}")

    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
