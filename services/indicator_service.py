from time import perf_counter

from database.manager import DatabaseManager
from config.logging_config import logger
from indicators.moving_averages.sma import SMAIndicator
from services.ohlcv_cache_access import fetch_ohlcv_frame


class IndicatorService:
    """
    Business workflow for calculating technical indicators.
    """

    def __init__(self, database_manager=None):
        self.db = database_manager or DatabaseManager()
        self.sma = SMAIndicator()

    def calculate_indicators(self):
        """
        Calculate all currently supported indicators.
        """

        return self.calculate_sma()

    def calculate_sma(self):
        """
        Calculate and persist SMA20, SMA50 and SMA200 for all active tickers.
        """

        tickers = self.db.get_all_tickers()

        results = {
            "tickers": len(tickers),
            "processed": 0,
            "processed_tickers": [],
            "skipped": 0,
            "skipped_tickers": [],
            "rows": 0,
            "elapsed_seconds": 0.0,
        }

        started_at = perf_counter()

        logger.info("Starting SMA calculation for %s tickers", len(tickers))

        for ticker in tickers:

            logger.info("Calculating SMA for %s", ticker)

            dataframe = fetch_ohlcv_frame(self.db, ticker)

            if dataframe.empty:
                logger.info("Skipping %s because no price history exists", ticker)
                results["skipped"] += 1
                results["skipped_tickers"].append(ticker)
                continue

            dataframe = self.sma.calculate(dataframe)
            dataframe["ticker"] = ticker

            self.db.save_sma(dataframe)

            results["processed"] += 1
            results["processed_tickers"].append(ticker)
            results["rows"] += len(dataframe)

        self.db.commit()

        results["elapsed_seconds"] = perf_counter() - started_at

        logger.info(
            "Finished SMA calculation: %s processed, %s skipped, %s rows in %.2fs",
            results["processed"],
            results["skipped"],
            results["rows"],
            results["elapsed_seconds"],
        )

        return results

    def close(self):
        self.db.close()
