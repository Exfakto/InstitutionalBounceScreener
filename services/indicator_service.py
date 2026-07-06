from time import perf_counter

from database.manager import DatabaseManager
from config.logging_config import logger
from indicators.moving_averages.sma import SMAIndicator
from services.ohlcv_cache_access import fetch_ohlcv_frame
from services.technical_indicator_engine import TechnicalIndicatorEngine


class IndicatorService:
    """
    Business workflow for calculating technical indicators.
    """

    def __init__(self, database_manager=None):
        self.db = database_manager or DatabaseManager()
        self.sma = SMAIndicator()
        self.technical_engine = TechnicalIndicatorEngine()

    def calculate_indicators(self):
        """
        Calculate all currently supported indicators.
        """

        return self.calculate_technical_indicators()

    def calculate_technical_indicators(self):
        """
        Calculate and persist v2.2 technical indicators for all active tickers.
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

        logger.info(
            "Starting technical indicator calculation for %s tickers",
            len(tickers),
        )

        for ticker in tickers:

            logger.info("Calculating technical indicators for %s", ticker)

            dataframe = fetch_ohlcv_frame(self.db, ticker)

            if dataframe.empty:
                logger.info("Skipping %s because no OHLCV history exists", ticker)
                results["skipped"] += 1
                results["skipped_tickers"].append(ticker)
                continue

            rows = self.ohlcv_rows(ticker, dataframe)
            result = self.technical_engine.calculate(rows, ticker=ticker)

            self.db.save_technical_indicators(result)

            results["processed"] += 1
            results["processed_tickers"].append(ticker)
            results["rows"] += len(rows)

        self.db.commit()

        results["elapsed_seconds"] = perf_counter() - started_at

        logger.info(
            "Finished technical indicator calculation: %s processed, %s skipped, %s rows in %.2fs",
            results["processed"],
            results["skipped"],
            results["rows"],
            results["elapsed_seconds"],
        )

        return results

    @staticmethod
    def ohlcv_rows(ticker, dataframe):
        rows = []
        for date, row in dataframe.sort_index().iterrows():
            rows.append(
                {
                    "ticker": ticker,
                    "date": str(date.date()) if hasattr(date, "date") else str(date),
                    "open": row.get("Open", row.get("open")),
                    "high": row.get("High", row.get("high")),
                    "low": row.get("Low", row.get("low")),
                    "close": row.get("Close", row.get("close")),
                    "volume": row.get("Volume", row.get("volume")),
                }
            )
        return rows

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
