from services.watchlist_service import WatchlistService


class WatchlistController:
    """
    Controller for watchlist workflows.
    """

    def __init__(self, watchlist_service=None):
        self.watchlist_service = watchlist_service or WatchlistService()

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
