from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)


class InteractiveCandlestickChart(QWidget):
    """
    Lightweight cached-data candlestick chart with wheel zoom and drag pan.
    """

    def __init__(self, rows=None, support_zones=None, bounce_markers=None, ema_values=None, parent=None):
        super().__init__(parent)
        self.rows = []
        self.support_zones = support_zones or []
        self.bounce_markers = bounce_markers or []
        self.ema_values = ema_values or {}
        self.zoom = 1.0
        self.offset = 0
        self.drag_start = None
        self.setMinimumHeight(320)
        self.setMouseTracking(True)
        self.set_data(rows or [], support_zones, bounce_markers, ema_values)

    def set_data(self, rows, support_zones=None, bounce_markers=None, ema_values=None):
        self.rows = [row for row in (rows or []) if self.valid_row(row)]
        self.support_zones = support_zones or []
        self.bounce_markers = bounce_markers or []
        self.ema_values = ema_values or {}
        self.offset = max(0, len(self.rows) - self.visible_count())
        self.update()

    def visible_count(self):
        if not self.rows:
            return 0
        return min(len(self.rows), max(20, int(90 / self.zoom)))

    @staticmethod
    def valid_row(row):
        return all(InteractiveCandlestickChart.number(row.get(key)) is not None for key in ("open", "high", "low", "close"))

    @staticmethod
    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def wheelEvent(self, event):
        if not self.rows:
            return
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        self.zoom = max(0.6, min(5.0, self.zoom * factor))
        self.offset = min(self.offset, max(0, len(self.rows) - self.visible_count()))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start = QPoint(event.position().toPoint())

    def mouseMoveEvent(self, event):
        if self.drag_start is None or not self.rows:
            return
        visible_count = self.visible_count()
        if visible_count <= 0:
            return
        dx = event.position().toPoint().x() - self.drag_start.x()
        candle_width = max(1, self.width() / max(1, visible_count))
        shift = int(dx / candle_width)
        if shift:
            self.offset = max(0, min(len(self.rows) - visible_count, self.offset - shift))
            self.drag_start = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        self.drag_start = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f8fafc"))

        if not self.rows:
            painter.setPen(QColor("#64748b"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Price history unavailable.")
            return

        margin = 16
        chart_rect = QRectF(margin, margin, self.width() - margin * 2, self.height() * 0.68)
        volume_rect = QRectF(margin, chart_rect.bottom() + 10, self.width() - margin * 2, self.height() - chart_rect.bottom() - 26)
        visible_count = self.visible_count()
        visible = self.rows[self.offset:self.offset + visible_count]
        highs = [self.number(row.get("high")) for row in visible]
        lows = [self.number(row.get("low")) for row in visible]
        ema_numbers = [self.number(value) for value in self.ema_values.values()]
        zone_numbers = [
            self.number(value)
            for zone in self.support_zones
            for value in (zone.get("low"), zone.get("high"))
        ]
        prices = [value for value in highs + lows + ema_numbers + zone_numbers if value is not None]
        min_price = min(prices)
        max_price = max(prices)
        if min_price == max_price:
            min_price *= 0.98
            max_price *= 1.02
        price_pad = (max_price - min_price) * 0.08
        min_price -= price_pad
        max_price += price_pad

        def y_for(price):
            return chart_rect.bottom() - ((price - min_price) / (max_price - min_price)) * chart_rect.height()

        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.drawRect(chart_rect)
        painter.drawRect(volume_rect)

        for zone in self.support_zones:
            low = self.number(zone.get("low"))
            high = self.number(zone.get("high"))
            if low is None or high is None:
                continue
            top = y_for(max(low, high))
            bottom = y_for(min(low, high))
            painter.fillRect(QRectF(chart_rect.left(), top, chart_rect.width(), max(2, bottom - top)), QColor(59, 130, 246, 36))

        step = chart_rect.width() / max(1, len(visible))
        body_width = max(2, step * 0.56)
        max_volume = max([self.number(row.get("volume")) or 0 for row in visible] or [1])

        for index, row in enumerate(visible):
            x = chart_rect.left() + index * step + step / 2
            open_price = self.number(row.get("open"))
            high = self.number(row.get("high"))
            low = self.number(row.get("low"))
            close = self.number(row.get("close"))
            volume = self.number(row.get("volume")) or 0
            color = QColor("#16a34a") if close >= open_price else QColor("#dc2626")
            painter.setPen(QPen(color, 1.3))
            painter.drawLine(x, y_for(high), x, y_for(low))
            top = y_for(max(open_price, close))
            bottom = y_for(min(open_price, close))
            painter.fillRect(QRectF(x - body_width / 2, top, body_width, max(2, bottom - top)), color)
            volume_height = 0 if max_volume <= 0 else (volume / max_volume) * volume_rect.height()
            painter.fillRect(QRectF(x - body_width / 2, volume_rect.bottom() - volume_height, body_width, volume_height), QColor(color.red(), color.green(), color.blue(), 95))

        ema_colors = {
            "ema20": QColor("#2563eb"),
            "ema50": QColor("#9333ea"),
            "ema200": QColor("#f97316"),
        }
        for key, value in self.ema_values.items():
            ema = self.number(value)
            if ema is None:
                continue
            y = y_for(ema)
            painter.setPen(QPen(ema_colors.get(key, QColor("#334155")), 1.5, Qt.DashLine))
            painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)
            painter.drawText(chart_rect.right() - 70, y - 4, key.upper())

        dates = {str(row.get("date")): index for index, row in enumerate(visible)}
        for marker in self.bounce_markers:
            marker_date = str(marker.get("date"))
            if marker_date not in dates:
                continue
            price = self.number(marker.get("support_price") or marker.get("low_price"))
            if price is None:
                continue
            x = chart_rect.left() + dates[marker_date] * step + step / 2
            y = y_for(price)
            painter.setPen(QPen(QColor("#0f172a"), 1))
            painter.setBrush(QColor("#facc15"))
            painter.drawEllipse(QRectF(x - 4, y - 4, 8, 8))


class CandidateDetailWindow(QDialog):
    """
    Professional read-only detail window for a selected candidate.
    """

    def __init__(self, candidate=None, detail=None, parent=None):
        super().__init__(parent)

        self.detail = detail or {}
        self.candidate = candidate or self.detail.get("candidate")
        self.summary_labels = {}
        self.overview_cards = {}
        self.section_labels = {}

        ticker = self.ticker_text()
        self.setWindowTitle(f"{ticker} Candidate Detail")
        self.resize(1120, 820)
        self.setMinimumSize(900, 640)

        self.build_ui()

    def build_ui(self):
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.header_label = QLabel(self.header_text())
        self.header_label.setObjectName("CandidateDetailHeader")
        layout.addWidget(self.header_label)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("CandidateDetailTabs")
        self.tabs.addTab(self.scrollable_tab(self.overview_tab()), "Overview")
        self.tabs.addTab(self.scrollable_tab(self.technicals_tab()), "Technicals")
        self.tabs.addTab(self.scrollable_tab(self.institutional_tab()), "Institutional")
        self.tabs.addTab(self.scrollable_tab(self.bounce_history_tab()), "Bounce History")
        self.tabs.addTab(self.scrollable_tab(self.risk_tab()), "Risk")
        layout.addWidget(self.tabs)

    def scrollable_tab(self, content):
        scroll = QScrollArea()
        scroll.setObjectName("CandidateDetailScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    def set_candidate(self, candidate=None, detail=None):
        self.detail = detail or {}
        self.candidate = candidate or self.detail.get("candidate")
        self.summary_labels = {}
        self.overview_cards = {}
        self.section_labels = {}

        self.setWindowTitle(f"{self.ticker_text()} Candidate Detail")

        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()

        self.build_ui()

    def overview_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.create_kpi_strip())

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        score_card = self.create_score_card()
        top_layout.addWidget(score_card, stretch=1)

        summary_grid = QGridLayout()
        summary_grid.setContentsMargins(0, 0, 0, 0)
        summary_grid.setHorizontalSpacing(10)
        summary_grid.setVerticalSpacing(10)

        cards = [
            ("company_name", "Company Name", self.company_text()),
            ("ticker", "Ticker", self.ticker_text()),
            ("exchange", "Exchange", self.exchange_text()),
            ("sector", "Sector", self.sector_text()),
            ("industry", "Industry", self.industry_text()),
            ("current_price", "Current Price", self.price_text()),
            ("latest_close_date", "Latest Close Date", self.latest_close_date_text()),
            ("latest_volume", "Latest Volume", self.latest_volume_text()),
            ("week_52_high", "52-Week High", self.week_52_high_text()),
            ("week_52_low", "52-Week Low", self.week_52_low_text()),
            ("primary_support", "Primary Support", self.primary_support_text()),
            ("bounce_success", "Bounce Success", self.bounce_success_text()),
            ("overall_rating", "Overall Rating", self.overall_rating_text()),
            ("signal", "Signal", self.signal_text()),
            ("opportunity", "Opportunity Rating", self.opportunity_text()),
            ("risk", "Risk Rating", self.risk_text()),
        ]

        for index, (key, title, value) in enumerate(cards):
            card, value_label = self.create_summary_card(title, value)
            self.summary_labels[key] = value_label
            self.overview_cards[key] = card
            summary_grid.addWidget(card, index // 2, index % 2)

        summary_container = QWidget()
        summary_container.setLayout(summary_grid)
        top_layout.addWidget(summary_container, stretch=3)

        layout.addLayout(top_layout)

        layout.addWidget(self.create_price_chart_section())
        layout.addWidget(self.create_trade_planning_section())
        layout.addWidget(self.create_trade_checklist_section())

        why_section = self.create_why_section()
        layout.addWidget(why_section)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlainText(self.summary_body_text())
        self.summary_text.setObjectName("CandidateDetailSummaryText")
        self.summary_text.setMinimumHeight(120)
        layout.addWidget(self.summary_text)
        return tab

    def create_kpi_strip(self):
        self.kpi_labels = {}
        section = QFrame()
        section.setObjectName("CandidateDetailWhySection")
        layout = QGridLayout(section)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)
        items = [
            ("overall", "Overall Score", self.kpi_value(("final_score", "score", "primary_score_value"))),
            ("technical", "Technical Score", self.kpi_value(("technical_score", "trend_score"))),
            ("bounce", "Bounce Score", self.kpi_value(("bounce_quality_score", "bounce_score", "bounce_success_pct"))),
            ("fundamental", "Fundamental Score", self.kpi_value(("fundamental_intelligence_score", "quality_score"))),
            ("risk", "Risk Score", self.kpi_value(("overall_risk_score", "risk_score"))),
            ("quality", "Quality Score", self.kpi_value(("quality_score", "fundamental_intelligence_score"))),
            ("signal", "Signal", self.signal_text()),
            ("risk_rating", "Risk Rating", self.risk_text()),
        ]
        for index, (key, title, value) in enumerate(items):
            card, label = self.create_summary_card(title, value)
            card.setObjectName("CandidateDetailTechnicalCard")
            label.setProperty("status", self.kpi_role(key, value))
            label.style().unpolish(label)
            label.style().polish(label)
            self.kpi_labels[key] = label
            layout.addWidget(card, index // 4, index % 4)
        return section

    def create_price_chart_section(self):
        section = QFrame()
        section.setObjectName("CandidateDetailWhySection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        title = QLabel("Interactive Price Research Chart")
        title.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(title)
        self.price_chart = InteractiveCandlestickChart(
            rows=self.price_history_rows(),
            support_zones=self.chart_support_zones(),
            bounce_markers=self.bounce_history_rows(),
            ema_values=self.chart_ema_values(),
        )
        self.price_chart.setObjectName("CandidateDetailCandlestickChart")
        layout.addWidget(self.price_chart)
        return section

    def create_trade_planning_section(self):
        self.trade_level_labels = {}
        section = QFrame()
        section.setObjectName("CandidateDetailWhySection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        title = QLabel("Trade Planning")
        title.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for index, (key, title_text, value, role) in enumerate(self.trade_level_items()):
            card, label = self.create_summary_card(title_text, value)
            card.setObjectName("CandidateDetailTechnicalCard")
            label.setProperty("status", role)
            label.style().unpolish(label)
            label.style().polish(label)
            self.trade_level_labels[key] = label
            if key == "primary_support":
                self.trade_level_labels["support"] = label
            grid.addWidget(card, index // 3, index % 3)
        layout.addLayout(grid)
        return section

    def create_trade_levels_section(self):
        return self.create_trade_planning_section()

    def create_trade_checklist_section(self):
        self.checklist_labels = {}
        section = QFrame()
        section.setObjectName("CandidateDetailWhySection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        title = QLabel("Trade Checklist")
        title.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for index, (key, title_text, passed, note) in enumerate(self.trade_checklist_items()):
            value = self.checklist_status_text(passed)
            if note:
                value = f"{value} - {note}"
            card, label = self.create_summary_card(title_text, value)
            card.setObjectName("CandidateDetailTechnicalCard")
            label.setProperty("status", self.checklist_role(passed))
            label.style().unpolish(label)
            label.style().polish(label)
            self.checklist_labels[key] = label
            grid.addWidget(card, index // 3, index % 3)
        layout.addLayout(grid)
        return section

    def create_score_card(self):
        card = QFrame()
        card.setObjectName("CandidateDetailScoreCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("Institutional Bounce Score")
        title.setObjectName("CandidateDetailCardTitle")
        title.setAlignment(Qt.AlignCenter)

        value = QLabel(self.score_text())
        value.setObjectName("CandidateDetailScoreValue")
        value.setAlignment(Qt.AlignCenter)
        self.summary_labels["score"] = value

        rating = QLabel(self.overall_rating_text())
        rating.setObjectName("CandidateDetailScoreRating")
        rating.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(value)
        layout.addWidget(rating)
        layout.addStretch()
        return card

    def create_summary_card(self, title, value):
        card = QFrame()
        card.setObjectName("CandidateDetailSummaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("CandidateDetailCardTitle")

        value_label = QLabel(value)
        value_label.setObjectName("CandidateDetailCardValue")
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value_label.setWordWrap(True)
        if value in {"N/A", "Data not available", "Institutional data not configured"}:
            value_label.setProperty("status", "missing")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def kpi_value(self, aliases):
        raw_value = self.first_existing(
            *[self.metrics().get(alias) for alias in aliases],
            *[self.candidate_value(alias) for alias in aliases],
        )
        number = self.number_value(raw_value)
        if number is None:
            return "Data not available"
        return self.format_score_value(number)

    def kpi_role(self, key, value):
        if key == "signal":
            text = str(value or "").lower()
            if any(word in text for word in ("strong", "buy")):
                return "positive"
            if any(word in text for word in ("watch", "hold")):
                return "watch"
            if any(word in text for word in ("avoid", "sell")):
                return "negative"
            return "missing"
        if key == "risk_rating":
            return self.risk_role(value, "rating")
        number = self.number_value(value)
        if number is None:
            return "missing"
        if key == "risk":
            if number <= 35:
                return "positive"
            if number <= 65:
                return "watch"
            return "negative"
        if number >= 75:
            return "positive"
        if number >= 50:
            return "watch"
        return "negative"

    def price_history_rows(self):
        rows = self.detail.get("price_history") or self.metrics().get("price_history") or []
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            normalized.append(
                {
                    "date": row.get("date"),
                    "open": self.first_existing(row.get("open"), row.get("Open"), row.get("close"), row.get("Close")),
                    "high": self.first_existing(row.get("high"), row.get("High"), row.get("close"), row.get("Close")),
                    "low": self.first_existing(row.get("low"), row.get("Low"), row.get("close"), row.get("Close")),
                    "close": self.first_existing(row.get("close"), row.get("Close")),
                    "volume": self.first_existing(row.get("volume"), row.get("Volume")),
                }
            )
        return normalized

    def chart_support_zones(self):
        low = self.number_value(
            self.first_existing(
                self.metrics().get("support_zone_low"),
                self.bounce_value_from_aliases(("support_zone_low",)),
            )
        )
        high = self.number_value(
            self.first_existing(
                self.metrics().get("support_zone_high"),
                self.bounce_value_from_aliases(("support_zone_high",)),
            )
        )
        support = self.number_value(
            self.first_existing(
                self.metrics().get("primary_support"),
                self.metrics().get("support_price"),
            )
        )
        if low is None and support is not None:
            low = support * 0.995
        if high is None and support is not None:
            high = support * 1.005
        return [{"low": low, "high": high}] if low is not None and high is not None else []

    def chart_ema_values(self):
        return {
            key: self.technical_value(key)
            for key in ("ema20", "ema50", "ema200")
            if self.technical_value(key) not in (None, "")
        }

    def trade_levels(self):
        levels = self.detail.get("trade_levels")
        if isinstance(levels, dict) and levels:
            return levels
        metrics_levels = self.metrics().get("trade_levels")
        if isinstance(metrics_levels, dict):
            return metrics_levels
        return {}

    def trade_level_items(self):
        levels = self.trade_levels()
        items = [
            ("ideal_buy_zone", "Ideal Buy Zone", self.buy_zone_text(levels), "positive"),
            ("current_price", "Current Price", self.price_text(), "neutral"),
            ("primary_support", "Primary Support", self.format_trade_price(self.first_existing(levels.get("support"), self.metrics().get("primary_support"), self.metrics().get("support_price"))), "positive"),
            ("support_zone_low", "Support Zone Low", self.format_trade_price(self.first_existing(levels.get("ideal_buy_zone_low"), self.metrics().get("support_zone_low"))), "positive"),
            ("support_zone_high", "Support Zone High", self.format_trade_price(self.first_existing(levels.get("ideal_buy_zone_high"), self.metrics().get("support_zone_high"))), "positive"),
            ("technical_stop", "Technical Stop", self.format_trade_price(levels.get("technical_stop")), "negative"),
            ("atr_stop", "ATR Stop", self.format_trade_price(levels.get("atr_stop")), "negative"),
            ("target_1", "Target 1", self.format_trade_price(levels.get("target_1")), "positive"),
            ("target_2", "Target 2", self.format_trade_price(levels.get("target_2")), "positive"),
            ("target_3", "Target 3", self.format_trade_price(levels.get("target_3")), "positive"),
            ("expected_return", "Expected Return", self.format_trade_percent(levels.get("expected_return_pct")), "positive"),
            ("risk_reward", "Risk / Reward", self.format_risk_reward(levels.get("risk_reward")), "watch"),
        ]
        return items

    def buy_zone_text(self, levels):
        low = self.format_trade_price(levels.get("ideal_buy_zone_low"))
        high = self.format_trade_price(levels.get("ideal_buy_zone_high"))
        if low == "Data not available" and high == "Data not available":
            return "Data not available"
        return f"{low} - {high}"

    def format_trade_price(self, value):
        number = self.number_value(value)
        return self.format_price_value(number) if number is not None else "Data not available"

    def format_trade_percent(self, value):
        number = self.number_value(value)
        return self.format_percent_value(number) if number is not None else "Data not available"

    def format_risk_reward(self, value):
        number = self.number_value(value)
        if number is None:
            return "Data not available"
        return f"{number:.2f}:1"

    def trade_checklist_items(self):
        trend_text = str(self.technical_value("trend") or self.technical_value("market_structure") or "").lower()
        distance = self.number_value(
            self.first_existing(
                self.technical_value("distance_to_support_pct"),
                self.metrics().get("distance_to_support_pct"),
            )
        )
        relative_volume = self.number_value(self.technical_value("relative_volume"))
        latest_volume = self.number_value(self.metrics().get("latest_volume") or self.metrics().get("volume"))
        support_strength = self.number_value(
            self.first_existing(
                self.metrics().get("support_strength_score"),
                self.metrics().get("support_strength"),
            )
        )
        support_tests = self.number_value(
            self.first_existing(
                self.metrics().get("support_tests"),
                self.metrics().get("bounce_count"),
                self.metrics().get("successful_support_tests"),
            )
        )
        risk_score = self.number_value(self.metrics().get("overall_risk_score") or self.metrics().get("risk_score"))
        fundamental_score = self.number_value(
            self.metrics().get("fundamental_intelligence_score") or self.metrics().get("quality_score")
        )
        bounce_success = self.number_value(
            self.first_existing(
                self.metrics().get("bounce_success_pct"),
                self.metrics().get("historical_bounce_success_rate"),
                self.metrics().get("bounce_success_rate"),
            )
        )
        return [
            ("trend_aligned", "Trend aligned", True if "bull" in trend_text or "positive" in trend_text else None if not trend_text else False, self.technical_value("trend")),
            ("near_support", "Near support", True if distance is not None and distance <= 5 else "warning" if distance is not None and distance <= 8 else None if distance is None else False, self.format_trade_percent(distance) if distance is not None else ""),
            ("support_validated", "Support validated", self.support_validated_status(support_strength, support_tests), self.support_validation_note(support_strength, support_tests)),
            ("bounce_history_positive", "Bounce history positive", True if bounce_success is not None and bounce_success >= 70 else None if bounce_success is None else False, self.format_trade_percent(bounce_success) if bounce_success is not None else ""),
            ("risk_acceptable", "Risk acceptable", True if risk_score is not None and risk_score <= 60 else None if risk_score is None else False, self.format_score_value(risk_score) if risk_score is not None else ""),
            ("fundamentals_acceptable", "Fundamentals acceptable", True if fundamental_score is not None and fundamental_score >= 60 else None if fundamental_score is None else False, self.format_score_value(fundamental_score) if fundamental_score is not None else ""),
            ("liquidity_acceptable", "Liquidity acceptable", self.liquidity_status(relative_volume, latest_volume), self.liquidity_note(relative_volume, latest_volume)),
        ]

    @staticmethod
    def checklist_status_text(status):
        if status is True:
            return "Pass"
        if status is False:
            return "Fail"
        if status == "warning":
            return "Warning"
        return "Data not available"

    @staticmethod
    def checklist_role(status):
        if status is True:
            return "positive"
        if status == "warning":
            return "watch"
        if status is False:
            return "negative"
        return "missing"

    @staticmethod
    def support_validated_status(support_strength, support_tests):
        if support_strength is None and support_tests is None:
            return None
        if (support_strength is None or support_strength >= 70) and (support_tests is None or support_tests >= 3):
            return True
        if (support_strength is not None and support_strength >= 50) or (support_tests is not None and support_tests >= 1):
            return "warning"
        return False

    def support_validation_note(self, support_strength, support_tests):
        parts = []
        if support_strength is not None:
            parts.append(f"{self.format_score_value(support_strength)} strength")
        if support_tests is not None:
            parts.append(f"{int(support_tests):,} tests")
        return ", ".join(parts)

    @staticmethod
    def liquidity_status(relative_volume, latest_volume):
        if relative_volume is None and latest_volume is None:
            return None
        if relative_volume is not None:
            if relative_volume >= 1:
                return True
            if relative_volume >= 0.75:
                return "warning"
            return False
        if latest_volume is not None:
            if latest_volume >= 1_000_000:
                return True
            if latest_volume >= 250_000:
                return "warning"
            return False
        return None

    def liquidity_note(self, relative_volume, latest_volume):
        if relative_volume is not None:
            return f"{relative_volume:.1f}x relative volume"
        if latest_volume is not None:
            return self.format_integer_value(latest_volume)
        return ""

    def create_why_section(self):
        section = QFrame()
        section.setObjectName("CandidateDetailWhySection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel("Why this candidate?")
        title.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(title)

        self.why_labels = []
        reasons = self.why_candidate_reasons()
        for reason in reasons:
            label = QLabel(reason)
            label.setObjectName("CandidateDetailWhyItem")
            label.setWordWrap(True)
            self.why_labels.append(label)
            layout.addWidget(label)

        return section

    def technicals_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QLabel("Professional Technical Analysis")
        header.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(header)

        self.technical_labels = {}

        for title, items in self.technical_sections():
            layout.addWidget(self.technical_section(title, items))

        summary_section = QFrame()
        summary_section.setObjectName("CandidateDetailWhySection")
        summary_layout = QVBoxLayout(summary_section)
        summary_layout.setContentsMargins(14, 12, 14, 12)
        summary_layout.setSpacing(8)

        summary_title = QLabel("Technical Summary")
        summary_title.setObjectName("CandidateDetailSectionTitle")
        self.technical_summary_label = QLabel(self.technical_summary_text())
        self.technical_summary_label.setObjectName("CandidateDetailWhyItem")
        self.technical_summary_label.setWordWrap(True)
        self.technical_summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.technical_summary_label)
        layout.addWidget(summary_section)
        layout.addStretch()
        return tab

    def technical_section(self, title, items):
        section = QFrame()
        section.setObjectName("CandidateDetailWhySection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(title_label)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        for index, (key, item_title, value, role) in enumerate(items):
            card, value_label = self.create_summary_card(item_title, value)
            card.setObjectName("CandidateDetailTechnicalCard")
            value_label.setProperty("status", role)
            value_label.style().unpolish(value_label)
            value_label.style().polish(value_label)
            self.technical_labels[key] = value_label
            grid.addWidget(card, index // 3, index % 3)

        layout.addLayout(grid)
        return section

    def technical_sections(self):
        return [
            (
                "Trend Analysis",
                [
                    self.technical_item(
                        "trend",
                        "Trend",
                        ("trend", "trend_label", "trend_score"),
                        value_type="trend",
                    ),
                    self.technical_item(
                        "market_structure",
                        "Market Structure",
                        ("market_structure", "structure", "price_structure"),
                        value_type="trend",
                    ),
                    self.technical_item(
                        "sma20",
                        "SMA 20",
                        ("sma20", "sma_20"),
                        value_type="price",
                    ),
                    self.technical_item(
                        "sma50",
                        "SMA 50",
                        ("sma50", "sma_50"),
                        value_type="price",
                    ),
                    self.technical_item(
                        "sma200",
                        "SMA 200",
                        ("sma200", "sma_200"),
                        value_type="price",
                    ),
                    self.technical_item(
                        "ema20",
                        "EMA 20",
                        ("ema20", "ema_20", "ema20_price"),
                        value_type="price",
                    ),
                    self.technical_item(
                        "ema50",
                        "EMA 50",
                        ("ema50", "ema_50", "ema50_price"),
                        value_type="price",
                    ),
                    self.technical_item(
                        "ema200",
                        "EMA 200",
                        ("ema200", "ema_200", "ema200_price"),
                        value_type="price",
                    ),
                ],
            ),
            (
                "Momentum",
                [
                    self.technical_item(
                        "rsi",
                        "RSI (14)",
                        ("rsi", "rsi14"),
                        value_type="rsi_status",
                    ),
                    self.technical_item(
                        "macd",
                        "MACD",
                        ("macd", "macd_value"),
                        value_type="signed_status",
                    ),
                    self.technical_item(
                        "signal_line",
                        "Signal Line",
                        ("signal_line", "macd_signal", "macd_signal_line"),
                        value_type="signed_status",
                    ),
                    self.technical_item(
                        "macd_histogram",
                        "MACD Histogram",
                        ("macd_histogram", "histogram", "macd_hist"),
                        value_type="signed_status",
                    ),
                    self.technical_item(
                        "atr",
                        "ATR (14)",
                        ("atr", "atr14"),
                        value_type="number",
                    ),
                    self.technical_item(
                        "relative_strength",
                        "Relative Strength vs SPY",
                        (
                            "relative_strength_spy",
                            "relative_strength_vs_spy",
                            "relative_strength",
                            "relative_strength_score",
                        ),
                        value_type="score_status",
                    ),
                ],
            ),
            (
                "Volume & EMA Distance",
                [
                    self.technical_item(
                        "vwap",
                        "VWAP",
                        ("vwap",),
                        value_type="price",
                    ),
                    self.technical_item(
                        "average_volume_20",
                        "Average Volume 20",
                        ("average_volume_20", "avg_volume20", "avg_volume_20"),
                        value_type="integer",
                    ),
                    self.technical_item(
                        "relative_volume",
                        "Relative Volume",
                        ("relative_volume",),
                        value_type="number",
                    ),
                    self.technical_item(
                        "distance_from_ema20",
                        "Distance From EMA20",
                        ("distance_from_ema20",),
                        value_type="percent",
                    ),
                    self.technical_item(
                        "distance_from_ema50",
                        "Distance From EMA50",
                        ("distance_from_ema50",),
                        value_type="percent",
                    ),
                    self.technical_item(
                        "distance_from_ema200",
                        "Distance From EMA200",
                        ("distance_from_ema200",),
                        value_type="percent",
                    ),
                ],
            ),
            (
                "Support Analysis",
                [
                    self.technical_item(
                        "primary_support",
                        "Primary Support",
                        ("primary_support", "support_price", "support_level"),
                        value_type="price",
                    ),
                    self.technical_item(
                        "support_strength",
                        "Support Strength",
                        ("support_strength", "support_strength_score", "support_score"),
                        value_type="confidence",
                    ),
                    self.technical_item(
                        "distance_to_support",
                        "Distance From Support %",
                        ("distance_to_support", "distance_to_support_pct", "support_distance"),
                        value_type="percent_low_good",
                    ),
                    self.technical_item(
                        "historical_tests",
                        "Number of Historical Tests",
                        ("support_tests", "support_test_count", "successful_support_tests", "bounce_count"),
                        value_type="integer",
                    ),
                    self.technical_item(
                        "bounce_success_rate",
                        "Bounce Success Rate",
                        ("bounce_success_rate", "bounce_success_pct", "historical_bounce_success_rate", "bounce_probability"),
                        value_type="percent_high_good",
                    ),
                    self.technical_item(
                        "average_historical_bounce",
                        "Average Historical Bounce",
                        ("average_historical_bounce", "average_bounce", "avg_bounce", "average_bounce_pct"),
                        value_type="percent_high_good",
                    ),
                    self.technical_item(
                        "support_confidence",
                        "Support Confidence",
                        ("support_confidence", "support_confidence_score", "confidence"),
                        value_type="confidence",
                    ),
                ],
            ),
        ]

    def technical_item(self, key, title, aliases, value_type="number"):
        raw_value = self.first_existing(
            *[self.technical_value(alias) for alias in aliases]
        )
        if raw_value in (None, "") and key in self.v22_technical_keys():
            return key, title, "Coming in v2.2", "watch"
        display = self.format_technical_value(raw_value, value_type)
        return key, title, display, self.technical_role(raw_value, value_type)

    @staticmethod
    def v22_technical_keys():
        return {
            "relative_strength",
        }

    def technical_value(self, key):
        technical = self.detail.get("technical")
        if isinstance(technical, dict) and key in technical:
            return technical.get(key)

        metrics = self.metrics()
        if key in metrics:
            return metrics.get(key)

        return self.candidate_value(key)

    def format_technical_value(self, value, value_type):
        if value in (None, ""):
            return "Data not available"
        if value_type == "trend" and isinstance(value, str):
            return value

        number = self.number_value(value)
        if number is None:
            return str(value)

        if value_type == "price":
            return self.format_price_value(number)
        if value_type in {"percent", "percent_high_good", "percent_low_good"}:
            return self.format_percent_value(number)
        if value_type == "integer":
            return self.format_integer_value(number)
        if value_type == "confidence":
            return self.format_score_value(number, suffix=" / 100")
        if value_type == "rsi_status":
            return f"{self.format_score_value(number)} ({self.technical_status_text(value, value_type)})"
        if value_type in {"signed_status", "score_status"}:
            return f"{self.format_score_value(number)} ({self.technical_status_text(value, value_type)})"
        return self.format_score_value(number)

    def technical_status_text(self, value, value_type):
        role = self.technical_role(value, value_type)
        if role == "positive":
            return "Bullish"
        if role == "negative":
            return "Bearish"
        if role == "watch":
            return "Neutral"
        return "Data not available"

    def technical_role(self, value, value_type):
        if value in (None, ""):
            return "missing"

        if value_type == "trend" and isinstance(value, str):
            normalized = value.lower()
            if "bull" in normalized or "up" in normalized or "positive" in normalized:
                return "positive"
            if "bear" in normalized or "down" in normalized or "weak" in normalized:
                return "negative"
            return "watch"

        number = self.number_value(value)
        if number is None:
            return "neutral"

        if value_type == "percent":
            if number <= 3:
                return "positive"
            if number <= 8:
                return "watch"
            return "negative"

        if value_type == "percent_low_good":
            if number <= 3:
                return "positive"
            if number <= 8:
                return "watch"
            return "negative"

        if value_type == "percent_high_good":
            if number >= 70:
                return "positive"
            if number >= 50:
                return "watch"
            return "negative"

        if value_type == "rsi_status":
            if 50 <= number <= 70:
                return "positive"
            if 40 <= number < 50 or 70 < number <= 75:
                return "watch"
            return "negative"

        if value_type == "signed_status":
            if number > 0:
                return "positive"
            if number < 0:
                return "negative"
            return "watch"

        if value_type == "score_status":
            if number >= 70:
                return "positive"
            if number >= 50:
                return "watch"
            return "negative"

        if value_type == "confidence":
            if number >= 75:
                return "positive"
            if number >= 50:
                return "watch"
            return "negative"

        if value_type == "price":
            return "neutral"

        if 45 <= number <= 70 and value_type == "score":
            return "positive"
        if number >= 70:
            return "positive"
        if number >= 50:
            return "watch"
        return "negative"

    def technical_summary_text(self):
        summary = []

        price = self.number_value(
            self.candidate_value("current_price")
            or self.candidate_value("price")
            or self.metrics().get("current_price")
            or self.metrics().get("price")
        )
        ema_values = [
            self.number_value(
                self.technical_value("ema20")
                or self.technical_value("ema_20")
                or self.technical_value("sma20")
            ),
            self.number_value(
                self.technical_value("ema50")
                or self.technical_value("ema_50")
                or self.technical_value("sma50")
            ),
            self.number_value(
                self.technical_value("ema200")
                or self.technical_value("ema_200")
                or self.technical_value("sma200")
            ),
        ]
        known_emas = [value for value in ema_values if value is not None]
        if price is not None and len(known_emas) == 3:
            if all(price > value for value in known_emas):
                summary.append("The stock remains above all major moving averages.")
            elif all(price < value for value in known_emas):
                summary.append("The stock is trading below all major moving averages.")
            else:
                summary.append("The stock is mixed relative to major moving averages.")
        else:
            summary.append("Moving average positioning is Data not available.")

        rsi = self.number_value(self.technical_value("rsi") or self.technical_value("rsi14"))
        macd = self.number_value(self.technical_value("macd") or self.technical_value("macd_value"))
        histogram = self.number_value(
            self.technical_value("macd_histogram") or self.technical_value("macd_hist")
        )
        if any(value is not None for value in (rsi, macd, histogram)):
            if (rsi is None or rsi >= 50) and (macd is None or macd > 0) and (
                histogram is None or histogram >= 0
            ):
                summary.append("Momentum is improving.")
            elif (rsi is not None and rsi < 45) or (macd is not None and macd < 0):
                summary.append("Momentum is weakening.")
            else:
                summary.append("Momentum is neutral.")
        else:
            summary.append("Momentum readings are Data not available.")

        distance = self.number_value(
            self.technical_value("distance_to_support_pct")
            or self.technical_value("distance_to_support")
            or self.technical_value("support_distance")
        )
        support_strength = self.number_value(
            self.technical_value("support_strength_score")
            or self.technical_value("support_strength")
            or self.technical_value("support_score")
        )
        if distance is not None and support_strength is not None:
            strength_text = "strong institutional" if support_strength >= 70 else "developing"
            summary.append(
                f"Price is trading within {distance:.1f}% of a {strength_text} support zone."
            )
        elif distance is not None:
            summary.append(f"Price is trading within {distance:.1f}% of support.")
        else:
            summary.append("Support proximity is Data not available.")

        bounce_probability = self.number_value(
            self.technical_value("bounce_probability")
            or self.technical_value("bounce_success_rate")
            or self.technical_value("historical_bounce_success_rate")
            or self.technical_value("bounce_score")
        )
        if bounce_probability is not None:
            if bounce_probability >= 70:
                summary.append("Historical bounce probability is high.")
            elif bounce_probability >= 50:
                summary.append("Historical bounce probability is moderate.")
            else:
                summary.append("Historical bounce probability is weak.")
        else:
            summary.append("Historical bounce probability is Data not available.")

        return "\n".join(summary)

    def institutional_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QLabel("Institutional Analysis")
        header.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(header)

        self.institutional_labels = {}

        for title, items in self.institutional_sections():
            layout.addWidget(self.institutional_section(title, items))

        outlook_card = QFrame()
        outlook_card.setObjectName("CandidateDetailInstitutionalOutlookCard")
        outlook_layout = QVBoxLayout(outlook_card)
        outlook_layout.setContentsMargins(16, 14, 16, 14)
        outlook_layout.setSpacing(6)

        outlook_title = QLabel("Institutional Outlook")
        outlook_title.setObjectName("CandidateDetailCardTitle")
        self.institutional_outlook_label = QLabel(self.institutional_outlook_text())
        self.institutional_outlook_label.setObjectName("CandidateDetailScoreRating")
        self.institutional_outlook_label.setAlignment(Qt.AlignCenter)
        self.institutional_outlook_label.setProperty(
            "status",
            self.institutional_outlook_role(),
        )
        self.institutional_outlook_label.style().unpolish(
            self.institutional_outlook_label
        )
        self.institutional_outlook_label.style().polish(
            self.institutional_outlook_label
        )

        outlook_layout.addWidget(outlook_title)
        outlook_layout.addWidget(self.institutional_outlook_label)

        self.institutional_summary_label = QLabel(self.institutional_summary_text())
        self.institutional_summary_label.setObjectName("CandidateDetailWhyItem")
        self.institutional_summary_label.setWordWrap(True)
        self.institutional_summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outlook_layout.addWidget(self.institutional_summary_label)

        layout.addWidget(outlook_card)
        layout.addStretch()
        return tab

    def institutional_section(self, title, items):
        section = QFrame()
        section.setObjectName("CandidateDetailWhySection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(title_label)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        for index, (key, item_title, value, role) in enumerate(items):
            card, value_label = self.create_summary_card(item_title, value)
            card.setObjectName("CandidateDetailInstitutionalCard")
            value_label.setProperty("status", role)
            value_label.style().unpolish(value_label)
            value_label.style().polish(value_label)
            self.institutional_labels[key] = value_label
            grid.addWidget(card, index // 3, index % 3)

        layout.addLayout(grid)
        return section

    def institutional_sections(self):
        return [
            (
                "Provider Intelligence",
                [
                    self.institutional_item(
                        "provider_status",
                        "Provider Status",
                        ("provider_status", "institutional_provider_status", "institutional_status", "status"),
                        value_type="status",
                    ),
                    self.institutional_item(
                        "institutional_score",
                        "Institutional Score",
                        ("institutional_score",),
                        value_type="score",
                    ),
                    self.institutional_item(
                        "smart_money_score",
                        "Smart Money Score",
                        ("smart_money_score",),
                        value_type="score",
                    ),
                    self.institutional_item(
                        "confidence_level",
                        "Confidence Level",
                        ("institutional_confidence_level", "confidence_level"),
                        value_type="text",
                    ),
                ],
            ),
            (
                "Ownership Summary",
                [
                    self.institutional_item(
                        "ownership",
                        "Institutional Ownership %",
                        ("institutional_ownership_pct", "institutional_ownership"),
                        value_type="percent_high_good",
                    ),
                    self.institutional_item(
                        "ownership_change_qoq",
                        "Ownership Change QoQ",
                        ("institutional_ownership_change_qoq", "ownership_change_qoq"),
                        value_type="signed_percent",
                    ),
                    self.institutional_item(
                        "ownership_trend",
                        "Ownership Trend",
                        ("ownership_trend",),
                        value_type="text",
                    ),
                    self.institutional_item(
                        "holder_count",
                        "Institutional Holders Count",
                        ("institutional_holders", "holder_count", "holders"),
                        value_type="integer",
                    ),
                    self.institutional_item(
                        "holder_change",
                        "Institutional Holders Change",
                        ("institutional_holders_change", "holder_change", "holders_change_qoq"),
                        value_type="signed_integer",
                    ),
                ],
            ),
            (
                "Institutional Flow",
                [
                    self.institutional_item(
                        "net_buying",
                        "Net Institutional Buying",
                        ("net_institutional_buying", "thirteen_f_net_change", "13f_net_change"),
                        value_type="currency",
                    ),
                    self.institutional_item(
                        "major_buyers",
                        "Major Buyers",
                        ("major_buyers", "top_buyers", "institutional_buyers"),
                        value_type="list",
                    ),
                    self.institutional_item(
                        "major_sellers",
                        "Major Sellers",
                        ("major_sellers", "top_sellers", "institutional_sellers"),
                        value_type="list",
                    ),
                ],
            ),
            (
                "13F Activity",
                [
                    self.institutional_item(
                        "recent_13f_activity",
                        "13F Summary",
                        (
                            "institutional_13f_summary",
                            "recent_13f_activity",
                            "13f_status",
                            "thirteen_f_status",
                            "latest_13f_filing_date",
                        ),
                        value_type="text",
                    ),
                    self.institutional_item(
                        "recent_13f_accumulation",
                        "Recent 13F Accumulation",
                        (
                            "recent_13f_accumulation",
                            "13f_accumulation",
                            "thirteen_f_accumulation",
                        ),
                        value_type="text",
                    ),
                ],
            ),
            (
                "Insider Activity",
                [
                    self.institutional_item(
                        "insider_buying",
                        "Insider Buying",
                        ("insider_buying", "insider_buying_flag", "insider_buying_score"),
                        value_type="flag_positive",
                    ),
                    self.institutional_item(
                        "insider_selling",
                        "Insider Selling",
                        ("insider_selling", "insider_selling_flag", "insider_selling_score"),
                        value_type="flag_negative",
                    ),
                    self.institutional_item(
                        "insider_net_activity",
                        "Insider Net Activity",
                        ("insider_net_activity", "net_insider_activity", "insider_net_buying"),
                        value_type="signed_text",
                    ),
                    self.institutional_item(
                        "insider_activity",
                        "Insider Activity",
                        ("insider_activity_summary",),
                        value_type="text",
                    ),
                    self.institutional_item(
                        "short_interest",
                        "Short Interest",
                        ("short_interest_pct", "short_interest"),
                        value_type="percent_low_good",
                    ),
                ],
            ),
        ]

    def institutional_items(self):
        return [
            item
            for _, section_items in self.institutional_sections()
            for item in section_items
        ]

    def institutional_item(self, key, title, aliases, value_type="text"):
        raw_value = self.first_existing(
            *[self.institutional_value(alias) for alias in aliases]
        )
        if raw_value in (None, "") and self.institutional_provider_not_configured():
            raw_value = "Provider not configured"
        display = self.format_institutional_value(raw_value, value_type)
        return key, title, display, self.institutional_role(raw_value, value_type)

    def institutional_provider_not_configured(self):
        status = self.first_existing(
            self.institutional_value("provider_status"),
            self.institutional_value("institutional_provider_status"),
            self.institutional_value("institutional_status"),
            self.institutional_value("status"),
        )
        return str(status or "").lower() == "provider not configured"

    def institutional_value(self, key):
        institutional = self.detail.get("institutional")
        if isinstance(institutional, dict) and key in institutional:
            return institutional.get(key)

        metrics = self.metrics()
        if key in metrics:
            return metrics.get(key)

        return self.candidate_value(key)

    def format_institutional_value(self, value, value_type):
        if value in (None, ""):
            return "Data not available"

        if value_type == "list":
            if isinstance(value, (list, tuple)):
                return (
                    ", ".join(str(item) for item in value)
                    if value
                    else "Data not available"
                )
            return str(value)

        if value_type in {"flag_positive", "flag_negative"}:
            if isinstance(value, bool):
                return "Yes" if value else "No"
            number = self.number_value(value)
            if number is not None:
                return "Yes" if number > 0 else "No"
            return str(value)

        number = self.number_value(value)

        if value_type == "status":
            return str(value)
        if value_type == "score":
            return self.format_score_value(number) if number is not None else str(value)
        if value_type == "percent_high_good":
            return self.format_percent_value(number) if number is not None else str(value)
        if value_type == "percent_low_good":
            return self.format_percent_value(number) if number is not None else str(value)
        if value_type == "signed_percent":
            return f"{number:+.1f}%" if number is not None else str(value)
        if value_type == "currency":
            return self.format_currency_value(number, value)
        if value_type == "integer":
            return self.format_integer_value(number) if number is not None else str(value)
        if value_type == "signed_integer":
            return f"{int(number):+,}" if number is not None else str(value)
        if value_type == "signed_text":
            if number is not None:
                return self.format_currency_value(number, value)
            return str(value)
        return str(value)

    @staticmethod
    def format_currency_value(number, original):
        if number is None:
            return str(original)
        prefix = "-" if number < 0 else ""
        absolute = abs(number)
        if absolute >= 1_000_000_000:
            return f"{prefix}${absolute / 1_000_000_000:.2f}B"
        if absolute >= 1_000_000:
            return f"{prefix}${absolute / 1_000_000:.2f}M"
        return f"{prefix}${absolute:,.0f}"

    def institutional_role(self, value, value_type):
        if value in (None, ""):
            return "missing"

        if value_type == "flag_positive":
            return "positive" if self.truthy_value(value) else "neutral"
        if value_type == "flag_negative":
            return "negative" if self.truthy_value(value) else "neutral"

        number = self.number_value(value)
        if number is None:
            text = str(value).lower()
            if "provider not configured" in text:
                return "missing"
            if any(word in text for word in ("current", "positive", "buying", "rising")):
                return "positive"
            if any(word in text for word in ("stale", "selling", "negative", "falling")):
                return "negative"
            return "neutral"

        if value_type == "score":
            if number >= 70:
                return "positive"
            if number >= 45:
                return "watch"
            return "negative"
        if value_type == "percent_high_good":
            if number >= 60:
                return "positive"
            if number >= 35:
                return "watch"
            return "negative"
        if value_type == "percent_low_good":
            if number <= 10:
                return "positive"
            if number <= 20:
                return "watch"
            return "negative"
        if value_type in {"signed_percent", "currency"}:
            if number > 0:
                return "positive"
            if number < 0:
                return "negative"
            return "neutral"
        if value_type in {"signed_integer", "signed_text"}:
            if number is not None:
                if number > 0:
                    return "positive"
                if number < 0:
                    return "negative"
                return "neutral"
            text = str(value).lower()
            if any(word in text for word in ("buying", "positive", "accumulation", "inflow")):
                return "positive"
            if any(word in text for word in ("selling", "negative", "distribution", "outflow")):
                return "negative"
            return "neutral"
        return "neutral"

    def institutional_outlook_text(self):
        score = self.institutional_outlook_score()
        if score is None:
            return "Unknown"
        if score >= 4:
            return "Strong Accumulation"
        if score >= 2:
            return "Accumulation"
        if score <= -2:
            return "Distribution"
        return "Neutral"

    def institutional_outlook_role(self):
        outlook = self.institutional_outlook_text()
        if outlook in {"Strong Accumulation", "Accumulation"}:
            return "positive"
        if outlook == "Distribution":
            return "negative"
        if outlook == "Neutral":
            return "watch"
        return "missing"

    def institutional_outlook_score(self):
        values_seen = 0
        score = 0

        ownership = self.number_value(
            self.first_existing(
                self.institutional_value("institutional_ownership_pct"),
                self.institutional_value("institutional_ownership"),
            )
        )
        if ownership is not None:
            values_seen += 1
            if ownership >= 60:
                score += 1
            elif ownership < 35:
                score -= 1

        ownership_change = self.number_value(
            self.first_existing(
                self.institutional_value("institutional_ownership_change_qoq"),
                self.institutional_value("ownership_change_qoq"),
            )
        )
        if ownership_change is not None:
                values_seen += 1
                score += 1 if ownership_change > 0 else -1 if ownership_change < 0 else 0

        holder_change = self.number_value(
            self.first_existing(
                self.institutional_value("institutional_holders_change"),
                self.institutional_value("holder_change"),
                self.institutional_value("holders_change_qoq"),
            )
        )
        if holder_change is not None:
            values_seen += 1
            score += 1 if holder_change > 0 else -1 if holder_change < 0 else 0

        net_buying = self.number_value(
            self.first_existing(
                self.institutional_value("net_institutional_buying"),
                self.institutional_value("thirteen_f_net_change"),
                self.institutional_value("13f_net_change"),
            )
        )
        if net_buying is not None:
            values_seen += 1
            score += 1 if net_buying > 0 else -1 if net_buying < 0 else 0

        accumulation = self.first_existing(
            self.institutional_value("recent_13f_accumulation"),
            self.institutional_value("13f_accumulation"),
            self.institutional_value("thirteen_f_accumulation"),
        )
        if accumulation not in (None, ""):
            values_seen += 1
            text = str(accumulation).lower()
            if any(word in text for word in ("strong", "accumulation", "buying", "positive")):
                score += 1
            elif any(word in text for word in ("distribution", "selling", "negative")):
                score -= 1

        buying = self.institutional_value("insider_buying_flag")
        if buying not in (None, ""):
            values_seen += 1
            score += 1 if self.truthy_value(buying) else 0

        selling = self.institutional_value("insider_selling_flag")
        if selling not in (None, ""):
            values_seen += 1
            score -= 1 if self.truthy_value(selling) else 0

        if values_seen == 0:
            return None
        return score

    def institutional_summary_text(self):
        outlook = self.institutional_outlook_text()
        ownership = self.number_value(
            self.first_existing(
                self.institutional_value("institutional_ownership_pct"),
                self.institutional_value("institutional_ownership"),
            )
        )
        holder_change = self.number_value(
            self.first_existing(
                self.institutional_value("institutional_holders_change"),
                self.institutional_value("holder_change"),
                self.institutional_value("holders_change_qoq"),
            )
        )
        activity = self.first_existing(
            self.institutional_value("recent_13f_accumulation"),
            self.institutional_value("13f_accumulation"),
            self.institutional_value("thirteen_f_accumulation"),
            self.institutional_value("recent_13f_activity"),
        )

        if outlook == "Unknown":
            if self.institutional_provider_not_configured():
                return "Provider not configured."
            return "Institutional data not configured."

        if outlook == "Distribution":
            lead = "Institutional sponsorship shows distribution risk."
        elif outlook == "Strong Accumulation":
            lead = "Institutional sponsorship appears strong."
        elif outlook == "Accumulation":
            lead = "Institutional sponsorship appears constructive."
        else:
            lead = "Institutional sponsorship appears neutral."

        details = []
        if ownership is not None:
            if ownership >= 60:
                details.append("Ownership is above 60%")
            elif ownership >= 35:
                details.append("ownership is moderate")
            else:
                details.append("ownership is below institutional leadership levels")
        else:
            details.append("ownership is not configured")

        if holder_change is not None:
            if holder_change > 0:
                details.append("holders increased last quarter")
            elif holder_change < 0:
                details.append("holders declined last quarter")
            else:
                details.append("holder count was flat last quarter")
        else:
            details.append("holder change is not configured")

        if activity not in (None, ""):
            details.append(f"recent 13F activity suggests {activity}")
        else:
            details.append("recent 13F activity is not configured")

        return f"{lead} " + ", ".join(details) + "."

    def bounce_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QLabel("Bounce History")
        header.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(header)

        self.bounce_summary_labels = {}

        layout.addWidget(
            self.bounce_section("Bounce Summary", self.bounce_summary_items())
        )
        layout.addWidget(
            self.bounce_section("Support Zone Details", self.support_zone_items())
        )

        table_title = QLabel("Historical Bounce Table")
        table_title.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(table_title)

        self.bounce_empty_label = QLabel("No historical bounce data available.")
        self.bounce_empty_label.setObjectName("EmptyStateLabel")
        self.bounce_empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.bounce_empty_label)

        self.bounce_history_table = QTableWidget(0, 7)
        self.bounce_history_table.setObjectName("CandidateDetailBounceTable")
        self.bounce_history_table.setHorizontalHeaderLabels(
            [
                "Date",
                "Support Price",
                "Low Price",
                "Peak Price",
                "Bounce %",
                "Days to Peak",
                "Successful",
            ]
        )
        self.bounce_history_table.verticalHeader().setVisible(False)
        self.bounce_history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.bounce_history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bounce_history_table.setAlternatingRowColors(True)
        self.bounce_history_table.setShowGrid(False)
        self.bounce_history_table.setMinimumHeight(220)
        self.bounce_history_table.verticalHeader().setDefaultSectionSize(34)
        self.bounce_history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.bounce_history_table.horizontalHeader().setHighlightSections(False)
        layout.addWidget(self.bounce_history_table)

        rows = self.bounce_history_rows()
        self.populate_bounce_history_table(rows)
        has_rows = bool(rows)
        self.bounce_empty_label.setVisible(not has_rows)
        self.bounce_history_table.setVisible(has_rows)

        interpretation = QFrame()
        interpretation.setObjectName("CandidateDetailWhySection")
        interpretation_layout = QVBoxLayout(interpretation)
        interpretation_layout.setContentsMargins(14, 12, 14, 12)
        interpretation_layout.setSpacing(8)

        interpretation_title = QLabel("Bounce Interpretation")
        interpretation_title.setObjectName("CandidateDetailSectionTitle")
        self.bounce_interpretation_label = QLabel(self.bounce_interpretation_text())
        self.bounce_interpretation_label.setObjectName("CandidateDetailWhyItem")
        self.bounce_interpretation_label.setWordWrap(True)
        self.bounce_interpretation_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        interpretation_layout.addWidget(interpretation_title)
        interpretation_layout.addWidget(self.bounce_interpretation_label)
        layout.addWidget(interpretation)
        layout.addStretch()
        return tab

    def bounce_section(self, title, items):
        section = QFrame()
        section.setObjectName("CandidateDetailWhySection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(title_label)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        for index, (key, item_title, value, role) in enumerate(items):
            card, value_label = self.create_summary_card(item_title, value)
            card.setObjectName("CandidateDetailTechnicalCard")
            value_label.setProperty("status", role)
            value_label.style().unpolish(value_label)
            value_label.style().polish(value_label)
            self.bounce_summary_labels[key] = value_label
            grid.addWidget(card, index // 4, index % 4)

        layout.addLayout(grid)
        return section

    def bounce_summary_items(self):
        return [
            self.bounce_summary_item(
                "support_tests",
                "Support Tests",
                ("support_tests", "support_test_count", "bounce_count"),
                "integer",
            ),
            self.bounce_summary_item(
                "successful_bounces",
                "Successful Bounces",
                (
                    "successful_bounces",
                    "successful_bounce_count",
                    "successful_support_tests",
                    "validated_bounces",
                ),
                "integer",
            ),
            self.bounce_summary_item(
                "success_pct",
                "Bounce Success %",
                (
                    "bounce_success_pct",
                    "bounce_success_rate",
                    "historical_bounce_success_rate",
                ),
                "percent_high_good",
            ),
            self.bounce_summary_item(
                "average_bounce",
                "Average Bounce",
                ("average_bounce", "avg_bounce", "average_bounce_pct"),
                "percent_high_good",
            ),
            self.bounce_summary_item(
                "median_bounce",
                "Median Bounce",
                ("median_bounce", "median_bounce_pct"),
                "percent_high_good",
            ),
            self.bounce_summary_item(
                "largest_bounce",
                "Largest Bounce",
                ("largest_bounce", "largest_bounce_pct", "max_bounce"),
                "percent_high_good",
            ),
            self.bounce_summary_item(
                "most_recent_bounce",
                "Most Recent Bounce",
                ("most_recent_bounce", "last_bounce", "last_bounce_date"),
                "text",
            ),
            self.bounce_summary_item(
                "failed_support_breaks",
                "Failed Support Breaks",
                ("failed_support_breaks", "support_failures", "failed_breaks"),
                "integer_high_bad",
            ),
        ]

    def support_zone_items(self):
        return [
            self.bounce_summary_item(
                "primary_support",
                "Primary Support",
                ("primary_support", "support_price", "support_level"),
                "price",
            ),
            self.bounce_summary_item(
                "support_zone_low",
                "Support Zone Low",
                ("support_zone_low", "support_low", "zone_low"),
                "price",
            ),
            self.bounce_summary_item(
                "support_zone_high",
                "Support Zone High",
                ("support_zone_high", "support_high", "zone_high"),
                "price",
            ),
            self.bounce_summary_item(
                "support_strength",
                "Support Strength",
                ("support_strength", "support_strength_score", "support_score"),
                "confidence",
            ),
        ]

    def bounce_summary_item(self, key, title, aliases, value_type):
        raw_value = self.bounce_value_from_aliases(aliases)
        display = self.format_bounce_value(raw_value, value_type)
        return key, title, display, self.bounce_role(raw_value, value_type)

    def bounce_value_from_aliases(self, aliases):
        bounce = self.detail.get("bounce")
        if isinstance(bounce, dict):
            value = self.first_existing(*[bounce.get(alias) for alias in aliases])
            if value is not None:
                return value

        metrics = self.metrics()
        value = self.first_existing(*[metrics.get(alias) for alias in aliases])
        if value is not None:
            return value

        return self.first_existing(*[self.candidate_value(alias) for alias in aliases])

    def bounce_value(self, key):
        bounce = self.detail.get("bounce")
        if isinstance(bounce, dict) and key in bounce:
            return bounce.get(key)

        metrics = self.metrics()
        if key in metrics:
            return metrics.get(key)

        return self.candidate_value(key)

    def bounce_history_rows(self):
        sources = [
            self.candidate_value("bounce_history"),
            self.detail.get("bounce_history"),
            self.metrics().get("bounce_history"),
        ]

        bounce_detail = self.detail.get("bounce")
        if isinstance(bounce_detail, dict):
            sources.append(bounce_detail.get("history"))

        bounce_metrics = self.metrics().get("bounce")
        if isinstance(bounce_metrics, dict):
            sources.append(bounce_metrics.get("history"))

        for source in sources:
            if isinstance(source, (list, tuple)):
                return list(source)
        return []

    def populate_bounce_history_table(self, rows):
        self.bounce_history_table.setRowCount(0)
        for row_index, row in enumerate(rows):
            self.bounce_history_table.insertRow(row_index)
            values = [
                self.format_value(
                    self.bounce_row_value(row, "date", "bounce_date", "validation_date")
                ),
                self.format_bounce_value(
                    self.bounce_row_value(
                        row,
                        "support_price",
                        "support",
                        "support_level",
                        "support_price_mid",
                    ),
                    "price",
                ),
                self.format_bounce_value(
                    self.bounce_row_value(
                        row,
                        "low_price",
                        "low",
                        "test_low",
                        "support_test_low",
                    ),
                    "price",
                ),
                self.format_bounce_value(
                    self.bounce_row_value(
                        row,
                        "peak_price",
                        "peak",
                        "high_price",
                        "peak_high",
                    ),
                    "price",
                ),
                self.format_bounce_value(
                    self.bounce_row_value(
                        row,
                        "bounce_pct",
                        "bounce_percent",
                        "bounce_return_pct",
                        "max_bounce_pct",
                    ),
                    "percent_high_good",
                ),
                self.format_bounce_value(
                    self.bounce_row_value(
                        row,
                        "days_to_peak",
                        "days_to_high",
                        "peak_days",
                    ),
                    "integer",
                ),
                self.format_successful_value(
                    self.bounce_row_value(
                        row,
                        "successful",
                        "is_successful",
                        "validated",
                        "passed",
                    )
                ),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {1, 2, 3, 4, 5}:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.bounce_history_table.setItem(row_index, column, item)

    def bounce_row_value(self, row, *keys):
        for key in keys:
            value = self.object_value(row, key)
            if value not in (None, ""):
                return value
        return None

    def format_bounce_value(self, value, value_type):
        if value in (None, ""):
            return "Data not available"
        if value_type == "text":
            return str(value)

        number = self.number_value(value)
        if number is None:
            return str(value)
        if value_type == "price":
            return self.format_price_value(number)
        if value_type == "integer":
            return self.format_integer_value(number)
        if value_type == "integer_high_bad":
            return self.format_integer_value(number)
        if value_type == "confidence":
            return self.format_score_value(number, suffix=" / 100")
        if value_type == "percent_high_good":
            return self.format_percent_value(number)
        return self.format_score_value(number)

    def format_successful_value(self, value):
        if value in (None, ""):
            return "Data not available"
        return "Yes" if self.truthy_value(value) else "No"

    def bounce_role(self, value, value_type):
        if value in (None, ""):
            return "missing"
        if value_type == "text":
            return "neutral"

        number = self.number_value(value)
        if number is None:
            return "neutral"
        if value_type == "percent_high_good":
            if number >= 70:
                return "positive"
            if number >= 40:
                return "watch"
            return "negative"
        if value_type == "integer_high_bad":
            if number >= 2:
                return "negative"
            if number == 1:
                return "watch"
            return "positive"
        if value_type == "confidence":
            if number >= 75:
                return "positive"
            if number >= 50:
                return "watch"
            return "negative"
        return "neutral"

    def bounce_interpretation_text(self):
        support_tests = self.first_existing(
            self.bounce_value_from_aliases(
                ("support_tests", "support_test_count", "bounce_count")
            ),
        )
        successful_bounces = self.first_existing(
            self.bounce_value_from_aliases(
                (
                    "successful_bounces",
                    "successful_bounce_count",
                    "successful_support_tests",
                    "validated_bounces",
                )
            ),
        )
        success_rate = self.first_existing(
            self.bounce_value_from_aliases(
                (
                    "bounce_success_rate",
                    "bounce_success_pct",
                    "historical_bounce_success_rate",
                )
            ),
        )
        average_bounce = self.first_existing(
            self.bounce_value_from_aliases(
                (
                    "average_historical_bounce",
                    "average_bounce",
                    "avg_bounce",
                    "average_bounce_pct",
                )
            ),
        )

        support_tests_number = self.number_value(support_tests)
        successful_number = self.number_value(successful_bounces)
        success_rate_number = self.number_value(success_rate)
        average_bounce_number = self.number_value(average_bounce)

        if all(
            value is None
            for value in (
                support_tests_number,
                successful_number,
                success_rate_number,
                average_bounce_number,
            )
        ):
            return "Bounce interpretation is Data not available."

        tests_text = (
            f"{int(support_tests_number):,} times"
            if support_tests_number is not None
            else "Data not available times"
        )
        success_text = (
            f"{success_rate_number:.1f}% success rate"
            if success_rate_number is not None
            else "Data not available success rate"
        )
        average_text = (
            f"{average_bounce_number:.1f}%"
            if average_bounce_number is not None
            else "Data not available"
        )

        if successful_number is not None:
            held_text = f"held {int(successful_number):,} of {tests_text}"
        else:
            held_text = f"held {tests_text}"

        return (
            f"This support zone has {held_text} with a {success_text} "
            f"and an average bounce of {average_text}."
        )

    def metrics_tab(self, title, key):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        values = self.detail.get(key) or self.metric_group(key)

        if values:
            for metric, value in values.items():
                label = QLabel(self.format_value(value))
                label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.section_labels[f"{key}.{metric}"] = label
                form.addRow(str(metric), label)
        else:
            label = QLabel("Data not available")
            label.setObjectName("EmptyStateLabel")
            self.section_labels[key] = label
            form.addRow(title, label)

        layout.addLayout(form)
        layout.addStretch()
        return tab

    def risk_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QLabel("Risk Analysis")
        header.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(header)

        self.risk_labels = {}
        for title, items in self.risk_sections():
            layout.addWidget(self.risk_section(title, items))

        warning_section = QFrame()
        warning_section.setObjectName("CandidateDetailWhySection")
        warning_layout = QVBoxLayout(warning_section)
        warning_layout.setContentsMargins(14, 12, 14, 12)
        warning_layout.setSpacing(8)

        warning_title = QLabel("Active Risk Warnings")
        warning_title.setObjectName("CandidateDetailSectionTitle")
        warning_layout.addWidget(warning_title)

        self.risk_warning_labels = []
        for warning in self.active_risk_warnings():
            label = QLabel(warning)
            label.setObjectName("CandidateDetailWhyItem")
            label.setWordWrap(True)
            self.risk_warning_labels.append(label)
            warning_layout.addWidget(label)

        layout.addWidget(warning_section)
        layout.addStretch()
        return tab

    def risk_section(self, title, items):
        section = QFrame()
        section.setObjectName("CandidateDetailWhySection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(title_label)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        for index, (key, item_title, value, role) in enumerate(items):
            card, value_label = self.create_summary_card(item_title, value)
            card.setObjectName("CandidateDetailInstitutionalCard")
            value_label.setProperty("status", role)
            value_label.style().unpolish(value_label)
            value_label.style().polish(value_label)
            self.risk_labels[key] = value_label
            self.section_labels[f"risk.{key}"] = value_label
            grid.addWidget(card, index // 3, index % 3)

        layout.addLayout(grid)
        return section

    def risk_sections(self):
        return [
            (
                "Risk Summary",
                [
                    self.risk_item(
                        "risk_rating",
                        "Risk Rating",
                        ("risk_rating", "risk_level", "rating"),
                        "rating",
                    ),
                    self.risk_item(
                        "overall_risk_score",
                        "Overall Risk Score",
                        ("overall_risk_score", "risk_score", "composite_risk_score"),
                        "risk_score",
                    ),
                ],
            ),
            (
                "Event Risk",
                [
                    self.risk_item(
                        "upcoming_earnings",
                        "Upcoming Earnings Date",
                        ("upcoming_earnings", "earnings_date", "next_earnings_date"),
                        "text",
                    ),
                    self.risk_item(
                        "earnings_within_7_days",
                        "Earnings Within 7 Days",
                        ("earnings_within_7_days", "earnings_soon", "near_term_earnings"),
                        "flag_negative",
                    ),
                ],
            ),
            (
                "Technical Risk",
                [
                    self.risk_item(
                        "short_interest",
                        "Short Interest",
                        ("short_interest", "short_interest_pct", "short_float_pct"),
                        "percent_high_bad",
                    ),
                    self.risk_item(
                        "price_below_200dma",
                        "Price Below 200 DMA",
                        ("price_below_200dma", "below_200_dma", "below_ema200"),
                        "flag_negative",
                    ),
                    self.risk_item(
                        "recent_support_break",
                        "Recent Support Break",
                        ("recent_support_break", "support_break", "recent_breakdown"),
                        "flag_negative",
                    ),
                    self.risk_item(
                        "support_failure_risk",
                        "Support Failure Risk",
                        ("support_failure_risk", "support_failure_risk_pct", "breakdown_risk"),
                        "percent_high_bad",
                    ),
                    self.risk_item(
                        "volatility",
                        "Volatility / ATR",
                        ("volatility", "volatility_pct", "atr_pct", "atr"),
                        "percent_high_bad",
                    ),
                    self.risk_item(
                        "price_above_support_10pct",
                        "Current Price More Than 10% Above Support",
                        (
                            "price_above_support_10pct",
                            "more_than_10pct_above_support",
                            "far_above_support",
                        ),
                        "flag_negative",
                    ),
                ],
            ),
            (
                "Financial Risk",
                [
                    self.risk_item(
                        "debt_to_equity",
                        "Debt to Equity",
                        ("debt_to_equity", "debt_equity", "debt_to_equity_ratio"),
                        "ratio_high_bad",
                    ),
                    self.risk_item(
                        "debt_risk",
                        "Debt Risk",
                        ("debt_risk", "debt_risk_score", "leverage_risk"),
                        "risk_score",
                    ),
                    self.risk_item(
                        "excessive_debt",
                        "Excessive Debt",
                        ("excessive_debt", "high_debt", "excess_debt_flag"),
                        "flag_negative",
                    ),
                ],
            ),
            (
                "Insider / Sentiment Risk",
                [
                    self.risk_item(
                        "heavy_insider_selling",
                        "Heavy Insider Selling",
                        ("heavy_insider_selling", "insider_selling_heavy", "heavy_selling"),
                        "flag_negative",
                    ),
                    self.risk_item(
                        "insider_selling_risk",
                        "Insider Selling Risk",
                        ("insider_selling_risk", "insider_selling_flag", "insider_selling_score"),
                        "risk_score",
                    ),
                ],
            ),
        ]

    def risk_items(self):
        return [item for _, section_items in self.risk_sections() for item in section_items]

    def risk_item(self, key, title, aliases, value_type):
        if key == "risk_rating":
            fallback_risk = self.risk_text()
            if fallback_risk in {"N/A", "Data not available"}:
                fallback_risk = None
            raw_value = self.first_existing(
                *[self.risk_value(alias) for alias in aliases],
                fallback_risk,
            )
        else:
            raw_value = self.first_existing(
                *[self.risk_value(alias) for alias in aliases]
            )
        display = self.format_risk_value(raw_value, value_type)
        return key, title, display, self.risk_role(raw_value, value_type)

    def risk_value(self, key):
        risk = self.detail.get("risk")
        if isinstance(risk, dict) and key in risk:
            return risk.get(key)

        metrics = self.metrics()
        if key in metrics:
            return metrics.get(key)

        return self.candidate_value(key)

    def format_risk_value(self, value, value_type):
        if value in (None, ""):
            return "Data not available"

        if value_type == "rating":
            label = self.object_value(value, "rating_label") or self.object_value(value, "label")
            return str(label or value)

        if value_type == "text":
            return str(value)

        if value_type == "flag_negative":
            if isinstance(value, bool):
                return "Yes" if value else "No"
            number = self.number_value(value)
            if number is not None:
                return "Yes" if number > 0 else "No"
            return str(value)

        number = self.number_value(value)
        if number is None:
            return str(value)

        if value_type == "percent_high_bad":
            return self.format_percent_value(number)
        if value_type == "ratio_high_bad":
            return f"{number:.2f}"
        if value_type == "risk_score":
            return self.format_score_value(number)
        return str(value)

    def risk_role(self, value, value_type):
        if value in (None, ""):
            return "missing"

        if value_type == "rating":
            text = self.format_risk_value(value, value_type).lower()
            if any(word in text for word in ("high", "elevated", "weak", "avoid")):
                return "negative"
            if any(word in text for word in ("moderate", "medium", "watch")):
                return "watch"
            if any(word in text for word in ("low", "strong", "controlled")):
                return "positive"
            return "missing"

        if value_type == "flag_negative":
            return "negative" if self.truthy_value(value) else "positive"

        if value_type == "text":
            return "neutral"

        number = self.number_value(value)
        if number is None:
            text = str(value).lower()
            if any(word in text for word in ("high", "elevated", "yes", "active")):
                return "negative"
            if any(word in text for word in ("moderate", "medium", "watch")):
                return "watch"
            if any(word in text for word in ("low", "none", "no", "controlled")):
                return "positive"
            return "neutral"

        if value_type == "percent_high_bad":
            if number >= 20:
                return "negative"
            if number >= 10:
                return "watch"
            return "positive"

        if value_type == "ratio_high_bad":
            if number >= 2:
                return "negative"
            if number >= 1:
                return "watch"
            return "positive"

        if value_type == "risk_score":
            if number >= 70:
                return "negative"
            if number >= 40:
                return "watch"
            return "positive"

        return "neutral"

    def active_risk_warnings(self):
        warnings = []
        warning_fields = [
            (
                ("earnings_within_7_days", "earnings_soon", "near_term_earnings"),
                "Earnings within 7 days",
            ),
            (
                ("price_below_200dma", "below_200_dma", "below_ema200"),
                "Price below 200-day moving average",
            ),
            (
                ("recent_support_break", "support_break", "recent_breakdown"),
                "Recent support break",
            ),
            (
                ("heavy_insider_selling", "insider_selling_heavy", "heavy_selling"),
                "Heavy insider selling",
            ),
            (
                (
                    "price_above_support_10pct",
                    "more_than_10pct_above_support",
                    "far_above_support",
                ),
                "Current price more than 10% above support",
            ),
            (("excessive_debt", "high_debt", "excess_debt_flag"), "Excessive debt"),
        ]

        for aliases, message in warning_fields:
            value = self.first_existing(*[self.risk_value(alias) for alias in aliases])
            if self.truthy_value(value):
                warnings.append(f"* {message}")

        if not warnings:
            return ["No major active risk warnings."]
        return warnings

    def header_text(self):
        ticker = self.ticker_text()
        company = self.company_text()
        if company in {"N/A", "Data not available"}:
            return ticker
        return f"{ticker} - {company}"

    def ticker_text(self):
        return self.format_value(self.candidate_value("ticker") or self.detail.get("ticker"))

    def company_text(self):
        return self.format_value(
            self.candidate_value("company_name")
            or self.candidate_value("company")
            or self.detail.get("company_name")
        )

    def exchange_text(self):
        return self.format_value(
            self.candidate_value("exchange")
            or self.metrics().get("exchange")
            or self.detail.get("exchange")
        )

    def sector_text(self):
        return self.format_value(
            self.candidate_value("sector")
            or self.metrics().get("sector")
            or self.detail.get("sector")
        )

    def industry_text(self):
        return self.format_value(
            self.candidate_value("industry")
            or self.metrics().get("industry")
            or self.detail.get("industry")
        )

    def price_text(self):
        value = self.candidate_value("current_price") or self.candidate_value("price")
        if value is None:
            metrics = self.metrics()
            value = metrics.get("current_price") or metrics.get("price")
        number = self.number_value(value)
        if number is None:
            return "Data not available"
        return f"${number:,.2f}"

    def latest_close_date_text(self):
        return self.format_value(self.metrics().get("latest_close_date"))

    def latest_volume_text(self):
        number = self.number_value(
            self.metrics().get("latest_volume") or self.metrics().get("volume")
        )
        if number is None:
            return "Data not available"
        return self.format_integer_value(number)

    def week_52_high_text(self):
        number = self.number_value(
            self.metrics().get("week_52_high") or self.metrics().get("high52")
        )
        if number is None:
            return "Data not available"
        return self.format_price_value(number)

    def week_52_low_text(self):
        number = self.number_value(
            self.metrics().get("week_52_low") or self.metrics().get("low52")
        )
        if number is None:
            return "Data not available"
        return self.format_price_value(number)

    def primary_support_text(self):
        number = self.number_value(
            self.metrics().get("primary_support")
            or self.metrics().get("support_price")
            or self.metrics().get("support_level")
        )
        if number is None:
            return "Data not available"
        return self.format_price_value(number)

    def bounce_success_text(self):
        number = self.number_value(
            self.metrics().get("bounce_success_pct")
            or self.metrics().get("bounce_success_rate")
            or self.metrics().get("historical_bounce_success_rate")
        )
        if number is None:
            return "Data not available"
        return self.format_percent_value(number)

    def score_text(self):
        value = self.candidate_value("primary_score_value")
        if value is None:
            value = self.candidate_value("institutional_bounce_score")
        number = self.number_value(value)
        if number is None:
            return "Data not available"
        return f"{number:.1f}"

    def signal_text(self):
        signal = self.candidate_value("signal")
        if signal:
            return str(signal)

        score = self.number_value(self.candidate_value("primary_score_value"))
        if score is None:
            return "Data not available"
        if score >= 85:
            return "Strong Buy"
        if score >= 70:
            return "Buy"
        if score >= 55:
            return "Watch"
        return "Avoid"

    def overall_rating_text(self):
        score = self.number_value(self.candidate_value("primary_score_value"))
        if score is None:
            score = self.number_value(self.candidate_value("institutional_bounce_score"))
        if score is None:
            return "Data not available"
        if score >= 85:
            return "Elite"
        if score >= 70:
            return "Strong"
        if score >= 55:
            return "Developing"
        return "Weak"

    def opportunity_text(self):
        opportunity = self.candidate_value("opportunity_rating")
        label = self.object_value(opportunity, "rating_label")
        score = self.number_value(self.object_value(opportunity, "rating_score"))
        if label and score is not None:
            return f"{label} {score:.1f}"
        if label:
            return str(label)
        return self.format_value(self.candidate_value("opportunity"))

    def risk_text(self):
        risk = self.candidate_value("risk_rating")
        label = self.object_value(risk, "rating_label") or self.object_value(risk, "label")
        if label:
            return str(label)
        return self.format_value(risk)

    def risk_reward_text(self):
        value = self.metrics().get("risk_reward") or self.candidate_value("risk_reward")
        number = self.number_value(value)
        if number is None:
            return "Data not available"
        return f"{number:.2f}:1"

    def summary_body_text(self):
        for value in [
            self.candidate_value("summary"),
            self.candidate_value("notes"),
            self.candidate_value("setup_quality"),
            self.object_value(self.candidate_value("trade_thesis"), "summary"),
        ]:
            if value:
                return str(value)
        return "Data not available"

    def why_candidate_reasons(self):
        explicit = self.first_existing(
            self.candidate_value("reasons"),
            self.metrics().get("reasons"),
        )
        if isinstance(explicit, (list, tuple)) and explicit:
            return [self.reason_text(reason) for reason in explicit]

        reasons = []
        metrics = self.metrics()
        ownership = self.number_value(
            metrics.get("institutional_ownership_pct")
            or metrics.get("institutional_score")
        )
        support_tests = self.number_value(
            metrics.get("successful_support_tests")
            or metrics.get("validated_bounces")
            or metrics.get("bounce_count")
        )
        relative_strength = self.number_value(metrics.get("relative_strength_score"))
        bounce_probability = self.number_value(
            metrics.get("bounce_probability")
            or metrics.get("historical_bounce_success_rate")
            or metrics.get("bounce_score")
        )

        if ownership is not None and ownership >= 60:
            reasons.append("Strong institutional ownership")
        if support_tests is not None and support_tests >= 3:
            reasons.append("Three successful support tests")
        if relative_strength is not None and relative_strength >= 70:
            reasons.append("Positive relative strength")
        if bounce_probability is not None and bounce_probability >= 70:
            reasons.append("High bounce probability")

        thesis = self.candidate_value("trade_thesis")
        strengths = self.object_value(thesis, "strengths")
        if not reasons and isinstance(strengths, (list, tuple)) and strengths:
            reasons.extend(strengths[:4])

        if not reasons:
            return ["Data not available"]

        return [self.reason_text(reason) for reason in reasons[:4]]

    @staticmethod
    def reason_text(reason):
        text = str(reason or "").strip()
        if not text:
            text = "Data not available"
        if text in {"N/A", "Data not available"}:
            return "Data not available"
        return f"* {text}"

    def metric_group(self, group):
        metrics = self.metrics()
        value = metrics.get(group)
        if isinstance(value, dict):
            return dict(value)
        return {}

    def metrics(self):
        value = self.candidate_value("metrics")
        if isinstance(value, dict):
            return value
        value = self.detail.get("metrics")
        return value if isinstance(value, dict) else {}

    def candidate_value(self, name):
        if self.candidate is None:
            return None
        if isinstance(self.candidate, dict):
            return self.candidate.get(name)
        return getattr(self.candidate, name, None)

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def object_value(source, name):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(name)
        return getattr(source, name, None)

    @staticmethod
    def number_value(value):
        if hasattr(value, "value"):
            value = value.value
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def truthy_value(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value > 0
        normalized = str(value or "").strip().lower()
        return normalized in {"1", "true", "yes", "y", "buying", "positive"}

    @staticmethod
    def format_value(value):
        if value in (None, ""):
            return "Data not available"
        return str(value)

    @staticmethod
    def format_price_value(number):
        return f"${number:,.2f}"

    @staticmethod
    def format_percent_value(number):
        return f"{number:.1f}%"

    @staticmethod
    def format_score_value(number, suffix=""):
        return f"{number:.1f}{suffix}"

    @staticmethod
    def format_integer_value(number):
        return f"{int(number):,}"
