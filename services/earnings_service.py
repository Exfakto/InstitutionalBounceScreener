from time import perf_counter

from analysis.earnings_score import EarningsScore
from config.logging_config import logger
from database.manager import DatabaseManager
from earnings import EarningsImporter


class EarningsService:
    """
    Imports and stores CSV-based earnings intelligence.
    """

    def __init__(self, csv_path=None):
        self.db = DatabaseManager()
        self.importer = EarningsImporter(csv_path)
        self.score = EarningsScore()

    def import_earnings(self):
        started_at = perf_counter()
        dataframe = self.importer.load()

        results = {
            "rows": len(dataframe),
            "imported": 0,
            "skipped": 0,
            "elapsed_seconds": 0.0,
        }

        if dataframe.empty:
            results["elapsed_seconds"] = perf_counter() - started_at
            logger.info("No earnings CSV rows found to import")
            return results

        records = []

        for _, row in dataframe.iterrows():
            record = row.to_dict()
            ticker = record.get("ticker")

            if ticker is None or str(ticker).strip() == "":
                results["skipped"] += 1
                continue

            scored = self.score.apply(record)
            records.append(scored)

        results["imported"] = self.db.save_earnings(records)
        results["elapsed_seconds"] = perf_counter() - started_at

        logger.info(
            "Imported %s earnings rows, skipped %s rows in %.2fs",
            results["imported"],
            results["skipped"],
            results["elapsed_seconds"],
        )

        return results

    def close(self):
        self.db.close()
