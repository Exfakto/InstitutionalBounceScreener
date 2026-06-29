import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
)

from market.downloader import download_multiple_stocks
from database.manager import DatabaseManager


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Institutional Bounce Screener")
        self.resize(1000, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Download button
        self.download_button = QPushButton("📥 Download Market Data")
        self.download_button.clicked.connect(self.download_data)

        layout.addWidget(self.download_button)

        # Log window
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        layout.addWidget(self.output)

    def log(self, text):
        self.output.append(text)
        QApplication.processEvents()

    def download_data(self):

        tickers = [
            "AAPL",
            "MSFT",
            "NVDA",
            "META",
            "AMZN",
            "GOOGL",
            "TSLA",
        ]

        self.output.clear()

        self.log("Starting download...\n")

        # Download market data
        market = download_multiple_stocks(tickers)

        # Save to SQLite
        db = DatabaseManager()

        for ticker, history in market.items():

            rows = db.save_price_history(ticker, history)

            self.log(f"✅ {ticker}: {rows} rows saved")

        total = db.get_total_rows()

        self.log("")
        self.log(f"📊 Database contains {total:,} rows")

        db.close()

        self.log("\n✅ Download Complete!")

def run():

    app = QApplication(sys.argv)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())