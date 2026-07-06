"""
Canonical access helpers for cached historical OHLCV rows.
"""

from __future__ import annotations

import pandas as pd


def fetch_ohlcv_rows(repository, ticker, start_date=None, end_date=None):
    if repository is None or not hasattr(repository, "fetch_ohlcv"):
        return []
    rows = repository.fetch_ohlcv(ticker, start_date=start_date, end_date=end_date)
    if rows is None:
        return []
    if hasattr(rows, "iterrows"):
        return frame_to_ohlcv_rows(rows)
    return list(rows or [])


def frame_to_ohlcv_rows(dataframe):
    if dataframe is None or dataframe.empty:
        return []
    rows = []
    for date, row in dataframe.iterrows():
        rows.append(
            {
                "date": str(date.date()) if hasattr(date, "date") else str(date),
                "open": row.get("Open", row.get("open")),
                "high": row.get("High", row.get("high")),
                "low": row.get("Low", row.get("low")),
                "close": row.get("Close", row.get("close")),
                "volume": row.get("Volume", row.get("volume")),
            }
        )
    return rows


def fetch_ohlcv_frame(repository, ticker, start_date=None, end_date=None):
    return ohlcv_rows_to_frame(
        fetch_ohlcv_rows(repository, ticker, start_date=start_date, end_date=end_date)
    )


def ohlcv_rows_to_frame(rows):
    dataframe = pd.DataFrame(list(rows or []))
    if dataframe.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    dataframe = dataframe.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    if "date" in dataframe.columns:
        dataframe["date"] = pd.to_datetime(dataframe["date"])
        dataframe = dataframe.sort_values("date").set_index("date")

    return dataframe[[column for column in ["Open", "High", "Low", "Close", "Volume"] if column in dataframe.columns]]
