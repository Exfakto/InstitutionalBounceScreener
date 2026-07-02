from analysis.watchlist_intelligence import WatchlistIntelligenceAnalyzer
from services.live_data_service import LiveDataService
from services.watchlist_service import WatchlistService


class WatchlistController:
    """
    Controller for watchlist workflows.
    """

    def __init__(self, watchlist_service=None, live_data_service=None):
        self.watchlist_service = watchlist_service or WatchlistService()
        self.live_data_service = live_data_service or LiveDataService()

    def add_candidate(self, ticker, company_name=None, notes=None):
        return self.watchlist_service.add_item(
            ticker,
            company_name=company_name,
            notes=notes,
            source="Candidate",
        )

    def update_item(self, item_id, status=None, notes=None):
        return self.watchlist_service.update_item(
            item_id,
            status=status,
            notes=notes,
        )

    def remove_item(self, item_id):
        return self.watchlist_service.remove_item(item_id)

    def get_items(self, status=None):
        return self.watchlist_service.get_items(status=status)

    def count_items(self, status=None):
        return self.watchlist_service.count_items(status=status)

    def get_watchlist_intelligence(self):
        result = self.watchlist_service.get_items()

        if not result.get("success"):
            return WatchlistIntelligenceAnalyzer().analyze([])

        return WatchlistIntelligenceAnalyzer().analyze(result.get("item") or [])

    def refresh_watchlist(self, tickers):
        quotes = {}

        for ticker in tickers or []:
            normalized_ticker = self.normalize_ticker(ticker)

            if normalized_ticker is None:
                continue

            result = self.live_data_service.get_price_history(normalized_ticker)

            if not result.success:
                quotes[normalized_ticker] = {
                    "success": False,
                    "message": result.message,
                    "warnings": result.warnings,
                }
                continue

            quote = self.quote_from_price_history(result.data)

            if quote is None:
                quotes[normalized_ticker] = {
                    "success": False,
                    "message": "Quote data unavailable.",
                    "warnings": [],
                }
                continue

            quotes[normalized_ticker] = {
                "success": True,
                **quote,
            }

        return {
            "success": True,
            "message": "Watchlist quotes refreshed.",
            "quotes": quotes,
        }

    @classmethod
    def quote_from_price_history(cls, history):
        rows = cls.rows_from_history(history)

        if not rows:
            return None

        latest = rows[-1]
        previous = rows[-2] if len(rows) > 1 else None
        last_price = cls.value_for(latest, "Close", "close", "last", "price")

        if last_price is None:
            return None

        previous_close = (
            cls.value_for(previous, "Close", "close", "last", "price")
            if previous is not None
            else None
        )
        daily_change = None
        percent_change = None

        if previous_close not in (None, 0):
            daily_change = last_price - previous_close
            percent_change = (daily_change / previous_close) * 100

        return {
            "last_price": last_price,
            "daily_change": daily_change,
            "percent_change": percent_change,
            "timestamp": cls.timestamp_for(history, latest),
        }

    @staticmethod
    def rows_from_history(history):
        if history is None:
            return []

        if hasattr(history, "to_dict"):
            try:
                return history.to_dict("records")
            except TypeError:
                pass

        if isinstance(history, (list, tuple)):
            return [row for row in history if row is not None]

        return []

    @staticmethod
    def timestamp_for(history, latest):
        history_index = getattr(history, "index", None)

        if history_index is not None and not callable(history_index):
            try:
                if len(history_index) > 0:
                    return str(history_index[-1])
            except TypeError:
                pass

        if isinstance(latest, dict):
            return (
                latest.get("timestamp")
                or latest.get("date")
                or latest.get("datetime")
            )

        return None

    @staticmethod
    def value_for(row, *keys):
        if row is None:
            return None

        for key in keys:
            value = row.get(key) if isinstance(row, dict) else getattr(row, key, None)

            if value is None:
                continue

            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        return None

    @staticmethod
    def normalize_ticker(ticker):
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        if not normalized:
            return None

        return normalized
