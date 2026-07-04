from PySide6.QtWidgets import QApplication

from ui.widgets.screening_results_panel import ScreeningResultsPanel


def app():
    return QApplication.instance() or QApplication([])


def test_full_market_ui_controls_and_active_state():
    app()
    panel = ScreeningResultsPanel()

    assert panel.update_full_market_universe_button.text() == "Update Universe"
    assert panel.refresh_full_market_data_button.text() == "Refresh Market Data"
    assert panel.run_full_market_scan_button.text() == "Run Full Market Scan"

    panel.set_full_market_active(True, "Running full market scan")
    assert panel.cancel_full_market_button.isEnabled() is True
    assert panel.run_full_market_scan_button.isEnabled() is False
    assert "Running" in panel.full_market_status_label.text()

    panel.set_full_market_active(False, "Full market ready")
    assert panel.cancel_full_market_button.isEnabled() is False
    assert panel.run_full_market_scan_button.isEnabled() is True


def test_full_market_ui_coverage_report_empty_and_warning_states():
    app()
    panel = ScreeningResultsPanel()

    panel.set_full_market_coverage_report({})
    assert "0/0" in panel.full_market_coverage_label.text()

    panel.set_full_market_coverage_report(
        {
            "ticker_count": 3,
            "scan_ready_count": 2,
            "ohlcv_covered_count": 2,
            "warnings": ["Missing fundamentals"],
        }
    )
    assert "2/3" in panel.full_market_coverage_label.text()
    assert "Missing fundamentals" in panel.full_market_issues_label.text()
