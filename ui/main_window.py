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


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Institutional Bounce Screener")
        self.resize(1000, 700)

        # Main widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Download button
        self.download_button = QPushButton("📥 Download Market Data")
        layout.addWidget(self.download_button)

        # Output window
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        # Button event
        self.download_button.clicked.connect(self.download_data)

    def log(self, message):
        self.output.append(message)

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

        self.log("Starting download...\n")

        market = download_multiple_stocks(tickers)

        for ticker, history in market.items():
            self.log(f"✅ {ticker}: {len(history)} rows downloaded")
            self.log(f"    Saved to data/{ticker}.csv")

        self.log("")
        self.log("✅ Download Complete!")


def run():

    app = QApplication(sys.argv)

    window = MainWindow()

    window.show()

    app.exec()