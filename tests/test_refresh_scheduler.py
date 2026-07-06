from services.refresh_scheduler import RefreshScheduler
from providers.provider_result import ProviderResult


class FakeLiveDataService:

    def __init__(self, failure=False):
        self.calls = []
        self.failure = failure

    def fetch_daily_ohlcv(self, ticker, start=None, end=None):
        self.calls.append((ticker, start, end))

        if self.failure:
            return ProviderResult.fail(
                "refresh failed",
                source="fake_live_data",
                warnings=["planned failure"],
            )

        return ProviderResult.ok(
            data={"ticker": ticker},
            message="refresh ok",
            source="fake_live_data",
        )

    def get_price_history(self, ticker, start=None, end=None):
        return self.fetch_daily_ohlcv(ticker, start=start, end=end)


class FakeTimer:
    created = []

    def __init__(self, interval, function):
        self.interval = interval
        self.function = function
        self.started = False
        self.cancelled = False
        self.daemon = False
        FakeTimer.created.append(self)

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        self.function()


def reset_fake_timers():
    FakeTimer.created = []


def build_scheduler(service=None, interval=None):
    reset_fake_timers()
    return RefreshScheduler(
        live_data_service=service or FakeLiveDataService(),
        refresh_interval=interval,
        timer_factory=FakeTimer,
    )


def test_start_stop():
    scheduler = build_scheduler()

    assert scheduler.start() is True
    assert scheduler.is_running() is True
    assert FakeTimer.created[0].started is True

    assert scheduler.stop() is True
    assert scheduler.is_running() is False
    assert FakeTimer.created[0].cancelled is True


def test_safe_repeated_start_stop():
    scheduler = build_scheduler()

    assert scheduler.start() is True
    assert scheduler.start() is False
    assert len(FakeTimer.created) == 1

    assert scheduler.stop() is True
    assert scheduler.stop() is False


def test_interval_changes():
    scheduler = build_scheduler(interval=10)
    scheduler.start()

    interval = scheduler.set_refresh_interval(30)

    assert interval == 30
    assert scheduler.refresh_interval == 30
    assert FakeTimer.created[0].cancelled is True
    assert FakeTimer.created[1].interval == 30
    assert FakeTimer.created[1].started is True


def test_invalid_interval_uses_default():
    scheduler = build_scheduler()

    interval = scheduler.set_refresh_interval(0)

    assert interval == RefreshScheduler.DEFAULT_INTERVAL_SECONDS


def test_register_ticker():
    scheduler = build_scheduler()

    assert scheduler.register_ticker(" aapl ") is True
    assert scheduler.refresh_now()["AAPL"].success is True


def test_unregister_ticker():
    service = FakeLiveDataService()
    scheduler = build_scheduler(service=service)
    scheduler.register_ticker("AAPL")

    assert scheduler.unregister_ticker("aapl") is True
    assert scheduler.refresh_now() == {}
    assert service.calls == []


def test_duplicate_ticker_ignored():
    service = FakeLiveDataService()
    scheduler = build_scheduler(service=service)

    assert scheduler.register_ticker("AAPL") is True
    assert scheduler.register_ticker(" aapl ") is False

    scheduler.refresh_now()

    assert service.calls == [("AAPL", None, None)]


def test_clear_tickers():
    service = FakeLiveDataService()
    scheduler = build_scheduler(service=service)
    scheduler.register_ticker("AAPL")
    scheduler.register_ticker("MSFT")

    scheduler.clear_tickers()

    assert scheduler.refresh_now() == {}
    assert service.calls == []


def test_refresh_now():
    service = FakeLiveDataService()
    scheduler = build_scheduler(service=service)
    scheduler.register_ticker("AAPL")
    scheduler.register_ticker("MSFT")

    results = scheduler.refresh_now()

    assert list(results) == ["AAPL", "MSFT"]
    assert all(result.success for result in results.values())
    assert service.calls == [
        ("AAPL", None, None),
        ("MSFT", None, None),
    ]


def test_callback_invocation():
    service = FakeLiveDataService()
    scheduler = build_scheduler(service=service)
    received = []
    scheduler.register_ticker("AAPL")

    assert scheduler.register_callback(lambda ticker, result: received.append((ticker, result))) is True
    scheduler.refresh_now()

    assert received[0][0] == "AAPL"
    assert received[0][1].success is True


def test_duplicate_and_invalid_callback_ignored():
    scheduler = build_scheduler()
    callback = lambda ticker, result: None

    assert scheduler.register_callback(callback) is True
    assert scheduler.register_callback(callback) is False
    assert scheduler.register_callback(None) is False


def test_callback_exception_does_not_stop_refresh():
    service = FakeLiveDataService()
    scheduler = build_scheduler(service=service)
    received = []
    scheduler.register_ticker("AAPL")

    def failing_callback(ticker, result):
        raise RuntimeError("planned callback failure")

    scheduler.register_callback(failing_callback)
    scheduler.register_callback(lambda ticker, result: received.append(ticker))

    results = scheduler.refresh_now()

    assert results["AAPL"].success is True
    assert received == ["AAPL"]


def test_provider_failure_handling():
    service = FakeLiveDataService(failure=True)
    scheduler = build_scheduler(service=service)
    received = []
    scheduler.register_ticker("AAPL")
    scheduler.register_callback(lambda ticker, result: received.append((ticker, result)))

    results = scheduler.refresh_now()

    assert results["AAPL"].success is False
    assert received[0][0] == "AAPL"
    assert received[0][1].message == "refresh failed"
    assert scheduler.is_running() is False


def test_provider_failure_does_not_stop_running_scheduler():
    service = FakeLiveDataService(failure=True)
    scheduler = build_scheduler(service=service, interval=5)
    scheduler.register_ticker("AAPL")
    scheduler.start()

    FakeTimer.created[0].fire()

    assert scheduler.is_running() is True
    assert len(FakeTimer.created) == 2
    assert FakeTimer.created[1].started is True


def test_empty_ticker_list():
    service = FakeLiveDataService()
    scheduler = build_scheduler(service=service)

    assert scheduler.refresh_now() == {}
    assert service.calls == []


def test_deterministic_scheduling():
    service = FakeLiveDataService()
    scheduler = build_scheduler(service=service, interval=5)
    scheduler.register_ticker("AAPL")
    scheduler.start()

    FakeTimer.created[0].fire()

    assert service.calls == [("AAPL", None, None)]
    assert scheduler.is_running() is True
    assert len(FakeTimer.created) == 2
    assert FakeTimer.created[1].interval == 5
    assert FakeTimer.created[1].started is True


def test_stop_prevents_reschedule_after_timer_fire():
    service = FakeLiveDataService()
    scheduler = build_scheduler(service=service, interval=5)
    scheduler.register_ticker("AAPL")
    scheduler.start()
    scheduler.stop()

    FakeTimer.created[0].fire()

    assert service.calls == [("AAPL", None, None)]
    assert len(FakeTimer.created) == 1
