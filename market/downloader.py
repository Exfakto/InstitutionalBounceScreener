import os
import yfinance as yf


def download_stock(ticker, period="1y"):
    """
    Download one stock from Yahoo Finance.
    """
    stock = yf.Ticker(ticker)
    return stock.history(period=period)


def save_stock_to_csv(ticker, history):
    """
    Save a stock's history to the data folder.
    """

    os.makedirs("data", exist_ok=True)

    filename = os.path.join("data", f"{ticker}.csv")

    history.to_csv(filename)

    return filename


def download_multiple_stocks(tickers, period="1y"):
    """
    Download multiple stocks and save each one as a CSV.
    """

    results = {}

    for ticker in tickers:

        print(f"Downloading {ticker}...")

        history = download_stock(ticker, period)

        save_stock_to_csv(ticker, history)

        results[ticker] = history

    return results