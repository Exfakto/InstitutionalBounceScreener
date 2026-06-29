import pandas as pd

from indicators.moving_averages.sma import SMAIndicator

prices = pd.DataFrame(
    {
        "Close": range(1, 251)
    }
)

indicator = SMAIndicator()

df = indicator.calculate(prices)

print(df.tail())

print()

print(SMAIndicator.latest_values(df))