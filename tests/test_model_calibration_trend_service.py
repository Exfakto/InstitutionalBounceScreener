from services.model_calibration_history_service import CalibrationHistoryItem
from services.model_calibration_trend_service import ModelCalibrationTrendService


class HistoryService:
    def __init__(self, rows):
        self.rows = rows
        self.limit = None

    def get_history(self, limit=25, offset=0):
        self.limit = limit
        return list(self.rows)


def history_item(index):
    return CalibrationHistoryItem(
        run_id=f"cal-{index}",
        timestamp=f"2026-01-{index:02d}T00:00:00Z",
        model_version="v1",
        sample_size=100 + index,
        overall_score=70 + index,
        status="COMPLETED",
    )


def test_model_calibration_trend_generates_points_oldest_to_newest():
    rows = [history_item(3), history_item(2), history_item(1)]
    service = ModelCalibrationTrendService(history_service=HistoryService(rows))

    trend = service.get_trend("Last 25")

    assert trend.insufficient_data is False
    assert [point.run_id for point in trend.points] == ["cal-1", "cal-2", "cal-3"]
    assert trend.points[-1].overall_score == 73.0
    assert trend.points[-1].sample_size == 103


def test_model_calibration_trend_reads_extended_metrics_from_dict_rows():
    rows = [
        {
            "run_id": "cal-2",
            "completed_at": "2026-01-02T00:00:00Z",
            "overall_score": 80,
            "precision": 0.7,
            "recall": 0.6,
            "f1_score": 0.65,
            "confidence_calibration_error": 0.08,
            "sample_size": 120,
        },
        {
            "run_id": "cal-1",
            "completed_at": "2026-01-01T00:00:00Z",
            "summary_metrics": {
                "overall_score": 75,
                "precision": 0.6,
                "recall": 0.5,
                "f1": 0.55,
                "calibration_error": 0.1,
                "signal_count": 90,
            },
        },
    ]

    trend = ModelCalibrationTrendService(history_service=HistoryService(rows)).get_trend()

    assert trend.points[0].precision == 0.6
    assert trend.points[0].f1_score == 0.55
    assert trend.points[0].confidence_calibration_error == 0.1
    assert trend.points[0].sample_size == 90
    assert trend.points[1].precision == 0.7


def test_model_calibration_trend_window_filtering():
    rows = [history_item(index) for index in range(60, 0, -1)]
    history = HistoryService(rows)

    trend = ModelCalibrationTrendService(history_service=history).get_trend("Last 10")

    assert history.limit == 10
    assert len(trend.points) == 10
    assert trend.points[0].run_id == "cal-51"
    assert trend.points[-1].run_id == "cal-60"


def test_model_calibration_trend_all_window_keeps_history():
    rows = [history_item(index) for index in range(3, 0, -1)]

    trend = ModelCalibrationTrendService(history_service=HistoryService(rows)).get_trend("All")

    assert trend.window == "All"
    assert len(trend.points) == 3


def test_model_calibration_trend_empty_and_single_run_are_insufficient():
    empty = ModelCalibrationTrendService(history_service=HistoryService([])).get_trend()
    single = ModelCalibrationTrendService(
        history_service=HistoryService([history_item(1)])
    ).get_trend()

    assert empty.insufficient_data is True
    assert empty.message == "Insufficient historical data"
    assert single.insufficient_data is True
    assert len(single.points) == 1
