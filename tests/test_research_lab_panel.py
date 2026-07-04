from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from ui.widgets.research_lab_panel import ResearchLabPanel


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


class FakeAnalyticsService:
    def __init__(self):
        self.calls = []

    def analyze(self, run_id=None):
        self.calls.append(run_id)
        return SimpleNamespace(
            overall=SimpleNamespace(
                total_samples=4,
                completed_samples=3,
                win_rate=2 / 3,
                average_return=3.5,
                median_return=2.0,
                average_drawdown=-1.25,
                average_max_gain=6.0,
                expectancy=3.5,
                profit_factor=2.4,
            ),
            forward_returns={
                "5d": SimpleNamespace(
                    horizon="5d",
                    count=3,
                    average=1.1,
                    median=1.0,
                    std_deviation=0.4,
                    best=2.0,
                    worst=-0.3,
                ),
                "20d": SimpleNamespace(
                    horizon="20d",
                    count=3,
                    average=3.5,
                    median=2.0,
                    std_deviation=1.2,
                    best=7.0,
                    worst=-1.0,
                ),
            },
            score_buckets={
                "90-100": SimpleNamespace(
                    label="90-100",
                    count=2,
                    win_rate=1.0,
                    average_return=5.0,
                    drawdown=-0.8,
                    expectancy=5.0,
                )
            },
            sector_performance={
                "Technology": SimpleNamespace(
                    label="Technology",
                    count=3,
                    win_rate=2 / 3,
                    average_return=3.5,
                    drawdown=-1.25,
                    expectancy=3.5,
                )
            },
            outcome_distribution={"win": 2, "loss": 1, "flat": 0, "incomplete": 1},
        )


class FakeCalibrationService:
    def __init__(self):
        self.calls = []

    def calibrate(self, run_id=None):
        self.calls.append(run_id)
        return SimpleNamespace(
            sample_count=4,
            ranked_components=[
                SimpleNamespace(
                    rank=1,
                    component="support_score",
                    predictive_power=0.42,
                    correlations={"20d": 0.37},
                ),
                SimpleNamespace(
                    rank=2,
                    component="institutional_score",
                    predictive_power=0.31,
                    correlations={"20d": 0.29},
                ),
            ],
            recommendations=[
                SimpleNamespace(
                    component="support_score",
                    action="increase weight",
                    predictive_power=0.42,
                    rationale="Support score led forward returns in validation.",
                )
            ],
        )


def test_research_lab_panel_refresh_populates_sections(app):
    analytics_service = FakeAnalyticsService()
    calibration_service = FakeCalibrationService()
    panel = ResearchLabPanel(
        analytics_service=analytics_service,
        calibration_service=calibration_service,
    )

    panel.refresh_lab(run_id=7)

    assert analytics_service.calls == [7]
    assert calibration_service.calls == [7]
    assert panel.status_label.text() == "3 completed samples"
    assert panel.validation_summary_table.item(0, 1).text() == "4"
    assert panel.validation_summary_table.item(2, 1).text() == "66.7%"
    assert panel.forward_returns_table.rowCount() == 2
    assert panel.forward_returns_table.item(0, 0).text() == "5d"
    assert panel.score_buckets_table.item(0, 0).text() == "90-100"
    assert panel.sector_performance_table.item(0, 0).text() == "Technology"
    assert panel.calibration_summary_table.item(0, 1).text() == "Support Score"
    assert panel.recommendations_table.item(0, 1).text() == "Increase Weight"


def test_research_lab_panel_empty_state_is_read_only(app):
    panel = ResearchLabPanel(
        analytics_service=FakeAnalyticsService(),
        calibration_service=FakeCalibrationService(),
    )

    assert panel.status_label.text() == "No validation analytics loaded"
    assert panel.validation_summary_table.rowCount() == 6
    assert panel.recommendations_table.rowCount() == 0
    assert panel.validation_summary_table.editTriggers().value == 0
