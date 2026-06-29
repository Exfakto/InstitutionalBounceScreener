import pandas as pd


class SMAIndicator:
    """
    Calculates Simple Moving Averages.
    """

    @staticmethod
    def calculate(df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()

        result["sma20"] = result["Close"].rolling(20).mean()
        result["sma50"] = result["Close"].rolling(50).mean()
        result["sma200"] = result["Close"].rolling(200).mean()

        return result
