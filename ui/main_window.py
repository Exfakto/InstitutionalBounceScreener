import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel,
)

from controllers.market_controller import MarketController


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.controller = MarketController()

        self.setWindowTitle("Institutional Bounce Screener")
        self.resize(1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # -----------------------------------------
        # Universe Section
        # -----------------------------------------

        layout.addWidget(QLabel("<h2>Market Universe</h2>"))

        self.universe_button = QPushButton("🌎 Update Universe")
        self.universe_button.clicked.connect(self.update_universe)

        layout.addWidget(self.universe_button)

        # -----------------------------------------
        # Market Data Section
        # -----------------------------------------

        layout.addWidget(QLabel("<h2>Market Data</h2>"))

        self.download_button = QPushButton("📥 Download Prices")
        self.download_button.clicked.connect(self.download_prices)

        layout.addWidget(self.download_button)

        # -----------------------------------------
        # Activity Log
        # -----------------------------------------

        layout.addWidget(QLabel("<h2>Activity Log</h2>"))

        self.output = QTextEdit()
        self.output.setReadOnly(True)

        layout.addWidget(self.output)

    # --------------------------------------------------

    def log(self, message):

        self.output.append(message)

        QApplication.processEvents()

    # --------------------------------------------------

    def update_universe(self):

        self.output.clear()

        self.log("Updating market universe...")
        self.log("")

        imported, total = self.controller.update_universe()

        self.log(f"✅ Imported {imported} stocks")
        self.log(f"📈 Universe Size: {total}")

        self.log("")
        self.log("Universe update complete.")

    # --------------------------------------------------

    def download_prices(self):

        self.output.clear()

        self.log("Downloading market prices...")
        self.log("")

        results, total_rows = self.controller.download_prices()

        if len(results) == 0:

            self.log("No stocks found.")
            return

        for ticker, rows in results.items():

            self.log(f"✅ {ticker}: {rows} rows saved")

        self.log("")
        self.log(f"📊 Total Price Records: {total_rows:,}")

        self.log("")
        self.log("Download complete.")