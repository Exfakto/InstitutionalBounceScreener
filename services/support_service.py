from time import perf_counter

from config.logging_config import logger
from database.manager import DatabaseManager
from support import SupportStrength, SupportZoneClusterer, SwingLowDetector


class SupportDetectionService:
    """
    Business workflow for support detection.
    """

    def __init__(self, database_manager=None):
        self.db = database_manager or DatabaseManager()
        self.detector = SwingLowDetector()
        self.clusterer = SupportZoneClusterer()
        self.strength = SupportStrength()

    def detect_support(self):
        """
        Detect and persist support levels for active tickers.
        """

        tickers = self.db.get_all_tickers()

        results = {
            "tickers": len(tickers),
            "processed": 0,
            "processed_tickers": [],
            "skipped": 0,
            "skipped_tickers": [],
            "zones": 0,
            "elapsed_seconds": 0.0,
        }

        started_at = perf_counter()

        logger.info("Starting support detection for %s tickers", len(tickers))

        for ticker in tickers:

            dataframe = self.db.get_price_history(ticker)

            if dataframe.empty:
                logger.info("Skipping %s because no price history exists", ticker)
                results["skipped"] += 1
                results["skipped_tickers"].append(ticker)
                continue

            swing_lows = self.detector.detect(dataframe)
            current_price = float(dataframe["Close"].iloc[-1])
            zones = self.clusterer.cluster(swing_lows, current_price)
            zones = self.strength.apply(zones)

            zones_written = self.db.save_support_levels(ticker, zones)

            if zones_written == 0:
                logger.info("Skipping %s because no support zones were found", ticker)
                results["skipped"] += 1
                results["skipped_tickers"].append(ticker)
                continue

            results["processed"] += 1
            results["processed_tickers"].append(ticker)
            results["zones"] += zones_written

        self.db.commit()

        results["elapsed_seconds"] = perf_counter() - started_at

        logger.info(
            "Finished support detection: %s processed, %s skipped, %s zones in %.2fs",
            results["processed"],
            results["skipped"],
            results["zones"],
            results["elapsed_seconds"],
        )

        return results

    def close(self):
        self.db.close()
