import json

from services.export_service import ExportService


def test_export_service_csv_export(tmp_path):
    service = ExportService()
    destination = tmp_path / "watchlist.csv"

    result = service.export_watchlist(
        [{"ticker": "AAPL", "status": "Watching"}],
        destination,
        "csv",
    )

    assert result["success"] is True
    assert result["path"] == str(destination)
    assert "ticker,status" in destination.read_text(encoding="utf-8")
    assert "AAPL,Watching" in destination.read_text(encoding="utf-8")


def test_export_service_json_export(tmp_path):
    service = ExportService()
    destination = tmp_path / "stats.json"

    result = service.export_portfolio_statistics(
        {"total_trades": 3, "win_rate": 66.7},
        destination,
        "json",
    )

    assert result["success"] is True
    assert json.loads(destination.read_text(encoding="utf-8"))["total_trades"] == 3


def test_export_service_invalid_path_fails_safely():
    service = ExportService()

    result = service.export_watchlist([], "", "csv")

    assert result["success"] is False
    assert "Destination path is required" in result["message"]


def test_export_service_overwrite_protection(tmp_path):
    service = ExportService()
    destination = tmp_path / "watchlist.csv"
    destination.write_text("existing", encoding="utf-8")

    result = service.export_watchlist(
        [{"ticker": "MSFT"}],
        destination,
        "csv",
    )

    assert result["success"] is False
    assert destination.read_text(encoding="utf-8") == "existing"


def test_export_service_allows_explicit_overwrite(tmp_path):
    service = ExportService()
    destination = tmp_path / "watchlist.csv"
    destination.write_text("existing", encoding="utf-8")

    result = service.export_watchlist(
        [{"ticker": "MSFT"}],
        destination,
        "csv",
        allow_overwrite=True,
    )

    assert result["success"] is True
    assert "MSFT" in destination.read_text(encoding="utf-8")


def test_export_service_empty_dataset(tmp_path):
    service = ExportService()
    destination = tmp_path / "empty.csv"

    result = service.export_trade_journal([], destination, "csv")

    assert result["success"] is True
    assert result["count"] == 0
    assert destination.read_text(encoding="utf-8") == ""


def test_export_service_research_summary_csv(tmp_path):
    service = ExportService()
    destination = tmp_path / "research.csv"

    result = service.export_research_summary(
        {"ticker": "NVDA", "summary": "Institutional setup."},
        destination,
        "csv",
    )

    assert result["success"] is True
    assert "ticker,summary" in destination.read_text(encoding="utf-8")


def test_export_service_unsupported_format(tmp_path):
    service = ExportService()

    result = service.export_strategy_analytics(
        {"total_trades": 1},
        tmp_path / "analytics.xlsx",
        "xlsx",
    )

    assert result["success"] is False
    assert "Unsupported export format" in result["message"]
