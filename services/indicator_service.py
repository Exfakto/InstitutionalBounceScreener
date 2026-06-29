from database.manager import DatabaseManager
from indicators.sma import SMAIndicator


class IndicatorService:

    def __init__(self):
        self.db = DatabaseManager()

    def calculate_sma(self):

        tickers = self.db.get_all_tickers()

        for ticker in tickers:

            print(f"Calculating SMA: {ticker}")

            df = self.db.get_price_history(ticker)

            if df.empty:
                continue

            df = SMAIndicator.calculate(df)
            df["ticker"] = ticker

            self.db.save_sma(df)

        self.db.commit()

        print("Done.")
