from controllers.export_controller import ExportController


class FakeExportService:
    def __init__(self):
        self.calls = []

    def export_watchlist(self, *args):
        self.calls.append(("watchlist", args))
        return {"success": True}

    def export_trade_journal(self, *args):
        self.calls.append(("trade_journal", args))
        return {"success": True}

    def export_portfolio_statistics(self, *args):
        self.calls.append(("portfolio_statistics", args))
        return {"success": True}

    def export_strategy_analytics(self, *args):
        self.calls.append(("strategy_analytics", args))
        return {"success": True}

    def export_research_summary(self, *args):
        self.calls.append(("research_summary", args))
        return {"success": True}

    def export_research_report(self, *args):
        self.calls.append(("research_report", args))
        return {"success": True}

    def export_watchlist_intelligence(self, *args):
        self.calls.append(("watchlist_intelligence", args))
        return {"success": True}


def test_export_controller_delegates_watchlist():
    service = FakeExportService()
    controller = ExportController(export_service=service)

    result = controller.export_watchlist([], "watchlist.csv", "csv", False)

    assert result["success"] is True
    assert service.calls == [("watchlist", ([], "watchlist.csv", "csv", False))]


def test_export_controller_delegates_trade_journal():
    service = FakeExportService()
    controller = ExportController(export_service=service)

    controller.export_trade_journal([], "trades.csv", "csv", True)

    assert service.calls == [("trade_journal", ([], "trades.csv", "csv", True))]


def test_export_controller_delegates_portfolio_statistics():
    service = FakeExportService()
    controller = ExportController(export_service=service)

    controller.export_portfolio_statistics({}, "portfolio.json")

    assert service.calls == [("portfolio_statistics", ({}, "portfolio.json", "json", False))]


def test_export_controller_delegates_strategy_analytics():
    service = FakeExportService()
    controller = ExportController(export_service=service)

    controller.export_strategy_analytics({}, "strategy.json")

    assert service.calls == [("strategy_analytics", ({}, "strategy.json", "json", False))]


def test_export_controller_delegates_research_summary():
    service = FakeExportService()
    controller = ExportController(export_service=service)

    controller.export_research_summary({}, "research.json")

    assert service.calls == [("research_summary", ({}, "research.json", "json", False))]


def test_export_controller_delegates_research_report():
    service = FakeExportService()
    controller = ExportController(export_service=service)

    controller.export_research_report({"title": "Report"}, "research.md", "markdown", True)

    assert service.calls == [
        ("research_report", ({"title": "Report"}, "research.md", "markdown", True))
    ]


def test_export_controller_delegates_watchlist_intelligence():
    service = FakeExportService()
    controller = ExportController(export_service=service)

    controller.export_watchlist_intelligence(
        {"summary": "Watchlist intelligence"},
        "watchlist-intelligence.md",
        "markdown",
        True,
    )

    assert service.calls == [
        (
            "watchlist_intelligence",
            (
                {"summary": "Watchlist intelligence"},
                "watchlist-intelligence.md",
                "markdown",
                True,
            ),
        )
    ]
