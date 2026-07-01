from database.manager import DatabaseManager


class WatchlistService:
    """
    Thin service wrapper for local watchlist persistence.
    """

    VALID_STATUSES = {
        "Watching",
        "Ready",
        "Entered",
        "Rejected",
        "Closed",
    }

    def __init__(self, database_manager=None):
        self.database_manager = database_manager or DatabaseManager()

    def add_item(
        self,
        ticker,
        company_name=None,
        status="Watching",
        notes=None,
        source=None,
    ):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.result(False, "Ticker is required.")

        normalized_status = self.normalize_status(status)

        if normalized_status is None:
            return self.result(False, "Invalid watchlist status.")

        existing = self.database_manager.get_watchlist_item_by_ticker(
            normalized_ticker
        )

        if existing is not None:
            return self.result(
                True,
                "Watchlist item already exists.",
                item=self.row_to_dict(existing),
                count=self.database_manager.count_watchlist_items(),
            )

        item = self.database_manager.add_watchlist_item(
            normalized_ticker,
            company_name=company_name,
            status=normalized_status,
            notes=notes,
            source=source,
        )

        if item is None:
            return self.result(False, "Watchlist item could not be added.")

        return self.result(
            True,
            "Watchlist item added.",
            item=self.row_to_dict(item),
            count=self.database_manager.count_watchlist_items(),
        )

    def update_item(self, item_id, status=None, notes=None):
        normalized_status = None

        if status is not None:
            normalized_status = self.normalize_status(status)
            if normalized_status is None:
                return self.result(False, "Invalid watchlist status.")

        item = self.database_manager.update_watchlist_item(
            item_id,
            status=normalized_status,
            notes=notes,
        )

        if item is None:
            return self.result(False, "Watchlist item not found.")

        return self.result(
            True,
            "Watchlist item updated.",
            item=self.row_to_dict(item),
        )

    def remove_item(self, item_id):
        removed = self.database_manager.remove_watchlist_item(item_id)

        if not removed:
            return self.result(
                False,
                "Watchlist item not found.",
                count=self.database_manager.count_watchlist_items(),
            )

        return self.result(
            True,
            "Watchlist item removed.",
            count=self.database_manager.count_watchlist_items(),
        )

    def get_items(self, status=None):
        normalized_status = None

        if status is not None:
            normalized_status = self.normalize_status(status)
            if normalized_status is None:
                return self.result(False, "Invalid watchlist status.", count=0)

        rows = self.database_manager.get_watchlist_items(normalized_status)
        items = [self.row_to_dict(row) for row in rows]

        return self.result(
            True,
            "Watchlist items retrieved.",
            item=items,
            count=len(items),
        )

    def get_item_by_ticker(self, ticker):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.result(False, "Ticker is required.")

        item = self.database_manager.get_watchlist_item_by_ticker(normalized_ticker)

        if item is None:
            return self.result(False, "Watchlist item not found.")

        return self.result(
            True,
            "Watchlist item retrieved.",
            item=self.row_to_dict(item),
        )

    def count_items(self, status=None):
        normalized_status = None

        if status is not None:
            normalized_status = self.normalize_status(status)
            if normalized_status is None:
                return self.result(False, "Invalid watchlist status.", count=0)

        return self.result(
            True,
            "Watchlist items counted.",
            count=self.database_manager.count_watchlist_items(normalized_status),
        )

    @classmethod
    def normalize_status(cls, status):
        if status is None:
            return "Watching"

        normalized = str(status).strip()

        for valid_status in cls.VALID_STATUSES:
            if normalized.lower() == valid_status.lower():
                return valid_status

        return None

    @staticmethod
    def normalize_ticker(ticker):
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        if not normalized:
            return None

        return normalized

    @staticmethod
    def row_to_dict(row):
        if row is None:
            return None

        return dict(row)

    @staticmethod
    def result(success, message, item=None, count=None):
        return {
            "success": success,
            "message": message,
            "item": item,
            "count": count,
        }
