from time import perf_counter

from bounce import BounceValidator
from config.logging_config import logger
from database.manager import DatabaseManager


class BounceValidationService:
    """
    Business workflow for validating support-zone bounces.
    """

    def __init__(self, database_manager=None):
        self.db = database_manager or DatabaseManager()
        self.validator = BounceValidator()

    def validate_bounces(self):
        """
        Validate all stored support levels against price history.
        """

        support_levels = self.db.get_all_support_levels()

        results = {
            "support_levels": len(support_levels),
            "processed": 0,
            "processed_tickers": [],
            "skipped": 0,
            "skipped_tickers": [],
            "validated": 0,
            "elapsed_seconds": 0.0,
        }

        started_at = perf_counter()
        validations = []
        price_history_by_ticker = {}

        logger.info(
            "Starting bounce validation for %s support levels",
            len(support_levels),
        )

        for support_level in support_levels:

            ticker = support_level["ticker"]

            if ticker not in price_history_by_ticker:
                price_history_by_ticker[ticker] = self.db.get_price_history(ticker)

            dataframe = price_history_by_ticker[ticker]

            if dataframe.empty:
                logger.info(
                    "Skipping %s support level %s because no price history exists",
                    ticker,
                    support_level["id"],
                )
                results["skipped"] += 1
                self._append_unique(results["skipped_tickers"], ticker)
                continue

            validation = self.validator.validate(dataframe, dict(support_level))
            validations.append(validation)

            results["processed"] += 1
            self._append_unique(results["processed_tickers"], ticker)

        results["validated"] = self.db.save_bounce_validations(validations)
        self.db.commit()

        results["elapsed_seconds"] = perf_counter() - started_at

        logger.info(
            "Finished bounce validation: %s processed, %s skipped, %s validated in %.2fs",
            results["processed"],
            results["skipped"],
            results["validated"],
            results["elapsed_seconds"],
        )

        return results

    @staticmethod
    def _append_unique(values, value):

        if value not in values:
            values.append(value)

    def close(self):
        self.db.close()
