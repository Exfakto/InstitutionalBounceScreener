from ui.main_window import MainWindow


class FakeMarketStatus:

    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = []

    def get_status(self, now=None):
        self.calls.append(now)
        status = self.statuses.pop(0) if self.statuses else "Open"
        return type("MarketStatusResult", (), {"status": status})()


class FakeRefreshScheduler:

    def __init__(self):
        self.interval = None
        self.started = 0
        self.stopped = 0
        self.cleared = 0
        self.tickers = []
        self.running = False

    def set_refresh_interval(self, seconds):
        self.interval = seconds
        return seconds

    def start(self):
        self.started += 1
        self.running = True
        return True

    def stop(self):
        self.stopped += 1
        self.running = False
        return True

    def is_running(self):
        return self.running

    def clear_tickers(self):
        self.cleared += 1
        self.tickers = []

    def register_ticker(self, ticker):
        self.tickers.append(ticker)
        return True


class FakeHeaderBar:

    def __init__(self):
        self.refresh_status = None

    def set_refresh_status(self, **kwargs):
        self.refresh_status = kwargs


def build_window(status):
    window = MainWindow.__new__(MainWindow)
    window.market_status_service = FakeMarketStatus([status])
    window.refresh_scheduler = FakeRefreshScheduler()
    window.header_bar = FakeHeaderBar()
    window.last_refresh_at = None
    window.next_refresh_at = None
    return window


def test_open_market_interval():
    window = build_window("Open")

    result = window.configure_live_refresh()

    assert result.status == "Open"
    assert window.refresh_scheduler.interval == 300
    assert window.refresh_scheduler.started == 1
    assert window.refresh_scheduler.stopped == 0
    assert window.header_bar.refresh_status["market_status"] == "Open"
    assert window.header_bar.refresh_status["auto_refresh"] is True
    assert window.header_bar.refresh_status["refresh_interval"] == 300


def test_pre_market_interval():
    window = build_window("Pre-market")

    window.configure_live_refresh()

    assert window.refresh_scheduler.interval == 600
    assert window.refresh_scheduler.started == 1


def test_after_hours_interval():
    window = build_window("After-hours")

    window.configure_live_refresh()

    assert window.refresh_scheduler.interval == 900
    assert window.refresh_scheduler.started == 1


def test_weekend_stop():
    window = build_window("Weekend")

    window.configure_live_refresh()

    assert window.refresh_scheduler.interval is None
    assert window.refresh_scheduler.started == 0
    assert window.refresh_scheduler.stopped == 1
    assert window.header_bar.refresh_status["market_status"] == "Weekend"
    assert window.header_bar.refresh_status["auto_refresh"] is False
    assert window.header_bar.refresh_status["refresh_interval"] is None


def test_holiday_stop():
    window = build_window("Holiday")

    window.configure_live_refresh()

    assert window.refresh_scheduler.interval is None
    assert window.refresh_scheduler.started == 0
    assert window.refresh_scheduler.stopped == 1
    assert window.header_bar.refresh_status["market_status"] == "Holiday"
    assert window.header_bar.refresh_status["auto_refresh"] is False


def test_overnight_interval():
    window = build_window("Closed")

    window.configure_live_refresh()

    assert window.refresh_scheduler.interval == 1800
    assert window.refresh_scheduler.started == 1


def test_scheduler_reused():
    window = build_window("Open")
    scheduler = window.refresh_scheduler

    window.configure_live_refresh()

    assert window.refresh_scheduler is scheduler


def test_interval_updates_when_market_status_changes():
    window = MainWindow.__new__(MainWindow)
    window.market_status_service = FakeMarketStatus(["Open", "After-hours"])
    window.refresh_scheduler = FakeRefreshScheduler()
    window.header_bar = FakeHeaderBar()
    window.last_refresh_at = None
    window.next_refresh_at = None

    first = window.configure_live_refresh()
    second = window.configure_live_refresh()

    assert first.status == "Open"
    assert second.status == "After-hours"
    assert window.refresh_scheduler.interval == 900
    assert window.refresh_scheduler.started == 2
    assert window.header_bar.refresh_status["market_status"] == "After-hours"
    assert window.header_bar.refresh_status["refresh_interval"] == 900


def test_register_refresh_tickers_reuses_scheduler():
    window = build_window("Open")
    scheduler = window.refresh_scheduler
    first = type("Candidate", (), {"ticker": "AAPL"})()
    second = {"ticker": "MSFT"}

    window.register_refresh_tickers([first, second])

    assert window.refresh_scheduler is scheduler
    assert scheduler.cleared == 1
    assert scheduler.tickers == ["AAPL", "MSFT"]


def test_refresh_completion_updates_header():
    window = build_window("Open")
    window.configure_live_refresh()

    window.mark_refresh_completed("manual-refresh")

    assert window.last_refresh_at != "manual-refresh"
    assert window.header_bar.refresh_status["last_refresh"] == window.last_refresh_at
