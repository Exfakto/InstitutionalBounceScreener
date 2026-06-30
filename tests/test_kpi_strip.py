import pytest
from PySide6.QtWidgets import QApplication

from ui.widgets.kpi_strip import KpiStrip


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def test_kpi_strip_displays_dashboard_statistics(app):
    strip = KpiStrip()

    strip.update_statistics(
        {
            "stocks": 123,
            "rows": 4567,
            "indicator_rows": 8901,
            "support_levels": 23,
            "validated_zones": 17,
        }
    )

    assert strip.value_for("stocks") == "123"
    assert strip.value_for("rows") == "4,567"
    assert strip.value_for("indicator_rows") == "8,901"
    assert strip.value_for("support_levels") == "23"
    assert strip.value_for("validated_zones") == "17"


def test_kpi_strip_contains_expected_cards(app):
    strip = KpiStrip()

    assert list(strip.cards) == [
        "stocks",
        "rows",
        "indicator_rows",
        "support_levels",
        "validated_zones",
    ]
