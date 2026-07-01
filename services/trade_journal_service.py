from database.manager import DatabaseManager


class TradeJournalService:
    """
    Thin service wrapper for paper trade journal persistence.
    """

    VALID_STATUSES = {
        "Watching",
        "Entered",
        "Exited Win",
        "Exited Loss",
        "Cancelled",
    }

    def __init__(self, database_manager=None):
        self.database_manager = database_manager or DatabaseManager()

    def create_trade(self, **trade_data):
        ticker = self.normalize_ticker(trade_data.get("ticker"))

        if ticker is None:
            return self.result(False, "Ticker is required.")

        status = self.normalize_status(trade_data.get("status", "Watching"))

        if status is None:
            return self.result(False, "Invalid trade status.")

        trade_data = dict(trade_data)
        trade_data["ticker"] = ticker
        trade_data["status"] = status

        trade = self.database_manager.create_trade(**trade_data)

        if trade is None:
            return self.result(False, "Trade could not be created.")

        return self.result(
            True,
            "Trade created.",
            trade=self.row_to_dict(trade),
            count=self.database_manager.count_trades(),
        )

    def update_trade(self, trade_id, **updates):
        normalized_updates = self.normalize_updates(updates)

        if normalized_updates is None:
            return self.result(False, "Invalid trade status.")

        trade = self.database_manager.update_trade(trade_id, **normalized_updates)

        if trade is None:
            return self.result(False, "Trade not found.")

        return self.result(
            True,
            "Trade updated.",
            trade=self.row_to_dict(trade),
        )

    def close_trade(
        self,
        trade_id,
        exit_date=None,
        exit_price=None,
        status="Exited Win",
        notes=None,
    ):
        normalized_status = self.normalize_status(status)

        if normalized_status is None:
            return self.result(False, "Invalid trade status.")

        trade = self.database_manager.close_trade(
            trade_id,
            exit_date=exit_date,
            exit_price=exit_price,
            status=normalized_status,
            notes=notes,
        )

        if trade is None:
            return self.result(False, "Trade not found.")

        return self.result(
            True,
            "Trade closed.",
            trade=self.row_to_dict(trade),
        )

    def delete_trade(self, trade_id):
        deleted = self.database_manager.delete_trade(trade_id)

        if not deleted:
            return self.result(
                False,
                "Trade not found.",
                count=self.database_manager.count_trades(),
            )

        return self.result(
            True,
            "Trade deleted.",
            count=self.database_manager.count_trades(),
        )

    def get_trade(self, trade_id):
        trade = self.database_manager.get_trade(trade_id)

        if trade is None:
            return self.result(False, "Trade not found.")

        return self.result(
            True,
            "Trade retrieved.",
            trade=self.row_to_dict(trade),
        )

    def get_trades(self, status=None, ticker=None):
        normalized_status = None

        if status is not None:
            normalized_status = self.normalize_status(status)
            if normalized_status is None:
                return self.result(False, "Invalid trade status.", trades=[], count=0)

        rows = self.database_manager.get_trades(
            status=normalized_status,
            ticker=self.normalize_ticker(ticker),
        )
        trades = [self.row_to_dict(row) for row in rows]

        return self.result(
            True,
            "Trades retrieved.",
            trades=trades,
            count=len(trades),
        )

    def count_trades(self, status=None):
        normalized_status = None

        if status is not None:
            normalized_status = self.normalize_status(status)
            if normalized_status is None:
                return self.result(False, "Invalid trade status.", count=0)

        return self.result(
            True,
            "Trades counted.",
            count=self.database_manager.count_trades(normalized_status),
        )

    @classmethod
    def normalize_updates(cls, updates):
        normalized = dict(updates)

        if "ticker" in normalized:
            normalized["ticker"] = cls.normalize_ticker(normalized["ticker"])
            if normalized["ticker"] is None:
                return None

        if "status" in normalized:
            normalized["status"] = cls.normalize_status(normalized["status"])
            if normalized["status"] is None:
                return None

        return normalized

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
    def result(success, message, trade=None, trades=None, count=None):
        return {
            "success": success,
            "message": message,
            "trade": trade,
            "trades": trades,
            "count": count,
        }
