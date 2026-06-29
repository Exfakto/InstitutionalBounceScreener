import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
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

        self.download_button = QPushButton("📥 Download Market Data")
        self.download_button.clicked.connect(self.download_market)

        layout.addWidget(self.download_button)

        self.output = QTextEdit()
        self.output.setReadOnly(True)

        layout.addWidget(self.output)

    def log(self, message):
        self.output.append(message)
        QApplication.processEvents()

    def download_market(self):

        self.output.clear()

        self.log("Downloading market data...")
        self.log("")

        results, total = self.controller.download_market()

        for ticker, rows in results.items():
            self.log(f"✅ {ticker}: {rows} rows stored")

        self.log("")
        self.log(f"📊 Database Rows : {total:,}")
        self.log("")
        self.log("Download Complete ✅")


def run():

    app = QApplication(sys.argv)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())