from services.trade_journal_service import TradeJournalService


class TradeJournalController:
    """
    Controller for paper trade journal workflows.
    """

    def __init__(self, trade_journal_service=None):
        self.trade_journal_service = trade_journal_service or TradeJournalService()

    def create_trade(self, **trade_data):
        return self.trade_journal_service.create_trade(**trade_data)

    def update_trade(self, trade_id, **updates):
        return self.trade_journal_service.update_trade(trade_id, **updates)

    def close_trade(
        self,
        trade_id,
        exit_date=None,
        exit_price=None,
        status="Exited Win",
        notes=None,
    ):
        return self.trade_journal_service.close_trade(
            trade_id,
            exit_date=exit_date,
            exit_price=exit_price,
            status=status,
            notes=notes,
        )

    def delete_trade(self, trade_id):
        return self.trade_journal_service.delete_trade(trade_id)

    def get_trades(self):
        return self.trade_journal_service.get_trades()

    def count_trades(self):
        return self.trade_journal_service.count_trades()
