import ccxt
import numpy as np
import pandas as pd
import talib
import time
import indicators

api_key = 'YOUR API KEY HERE'
secret_key = 'YOUR SECRET API KEY HERE'

binance = ccxt.binanceus({
    "apiKey": api_key,
    "secret": secret_key,
    "enableRateLimit": True
})

symbols = ["ETH/USD", "BTC/USD"]

def fetch_data(symbol, timeframe):
    data = binance.fetch_ohlcv(symbol, timeframe, limit=200)
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

def add_indicators(df):
    df["20_EMA"] = talib.EMA(df["close"], timeperiod=20)
    df["50_EMA"] = talib.EMA(df["close"], timeperiod=50)
    df["RSI"] = talib.RSI(df["close"], timeperiod=14)
    df["BB_upper"], df["BB_middle"], df["BB_lower"] = talib.BBANDS(df["close"], timeperiod=20)
    
    # Calculate the Ichimoku Cloud manually
    high_9_period = df["high"].rolling(window=9).max()
    low_9_period = df["low"].rolling(window=9).min()
    df["tenkan_sen"] = (high_9_period + low_9_period) / 2
    
    high_26_period = df["high"].rolling(window=26).max()
    low_26_period = df["low"].rolling(window=26).min()
    df["kijun_sen"] = (high_26_period + low_26_period) / 2
    
    df["senkou_span_a"] = ((df["tenkan_sen"] + df["kijun_sen"]) / 2).shift(26)

    high_52_period = df["high"].rolling(window=52).max()
    low_52_period = df["low"].rolling(window=52).min()
    df["senkou_span_b"] = ((high_52_period + low_52_period) / 2).shift(26)
    
    df["Ichimoku_cloud_top"] = df[["senkou_span_a", "senkou_span_b"]].max(axis=1)
    df["Ichimoku_cloud_bottom"] = df[["senkou_span_a", "senkou_span_b"]].min(axis=1)
    
    return df

def check_entry_conditions_long(df_5m, df_15m, df_1h):
    if (
        df_5m["close"].iloc[-1] > df_5m["20_EMA"].iloc[-1]
        and df_5m["RSI"].iloc[-1] > 40
        and df_15m["close"].iloc[-1] > df_15m["BB_middle"].iloc[-1]
        and df_1h["close"].iloc[-1] > df_1h["Ichimoku_cloud_top"].iloc[-1]
    ):
        return True
    return False

def check_entry_conditions_short(df_5m, df_15m, df_1h):
    if (
        df_5m["close"].iloc[-1] < df_5m["20_EMA"].iloc[-1]
        and df_5m["RSI"].iloc[-1] < 60
        and df_15m["close"].iloc[-1] < df_15m["BB_middle"].iloc[-1]
        and df_1h["close"].iloc[-1] < df_1h["Ichimoku_cloud_bottom"].iloc[-1]
    ):
        return True
    return False

def fibonacci_extensions(df):
    last_high = df['high'].iloc[-1]
    last_low = df['low'].iloc[-1]
    fib_levels = [1.272, 1.618, 2.0]
    fib_extensions = [(last_high - last_low) * level + last_low for level in fib_levels]
    return fib_extensions

def fibonacci_retracements(df):
    last_high = df['high'].rolling(window=2).max().iloc[-1]
    last_low = df['low'].rolling(window=2).min().iloc[-1]
    fib_levels = [0.382, 0.618, 0.786]
    fib_retracements = [last_low - (last_high - last_low) * level for level in fib_levels]
    return fib_retracements

def get_current_price(symbol):
    ticker = binance.fetch_ticker(symbol)
    current_price = ticker['last']
    return current_price

def main():
    while True:
        try:
            for symbol in symbols:
                df_5m = fetch_data(symbol, "5m")
                df_15m = fetch_data(symbol, "15m")
                df_1h = fetch_data(symbol, "1h")

                df_5m = add_indicators(df_5m)
                df_15m = add_indicators(df_15m)
                df_1h = add_indicators(df_1h)

                current_price = get_current_price(symbol)
                print(f"Current price of {symbol}: {current_price}")

                asset_name = symbol.split("/")[0]  # Get the asset name from the symbol

                # Check for long entry conditions
                if check_entry_conditions_long(df_5m, df_15m, df_1h):
                    entry_price = df_5m["close"].iloc[-1]
                    stop_loss = df_5m["BB_lower"].iloc[-1]

                    fib_extensions = fibonacci_extensions(df_1h)
                    take_profit_1, take_profit_2, take_profit_3 = fib_extensions

                    print(f"Long {asset_name} with an entry price of {entry_price:.2f}, "
                          f"a stop loss of {stop_loss:.2f}, and take profits at "
                          f"{take_profit_1:.2f}, {take_profit_2:.2f}, {take_profit_3:.2f}")

                # Check for short entry conditions
                if check_entry_conditions_short(df_5m, df_15m, df_1h):
                    entry_price = df_5m["close"].iloc[-1]
                    stop_loss = df_5m["BB_upper"].iloc[-1]

                    fib_retracements = fibonacci_retracements(df_1h)
                    take_profit_1, take_profit_2, take_profit_3 = fib_retracements

                    print(f"Short {asset_name} with an entry price of {entry_price:.2f}, "
                          f"a stop loss of {stop_loss:.2f}, and take profits at "
                          f"{take_profit_1:.2f}, {take_profit_2:.2f}, {take_profit_3:.2f}")

            countdown_duration = 5 * 60  # 5 minutes (300 seconds)
            for remaining_seconds in range(countdown_duration, 0, -1):
                remaining_time_str = f"Next trade check in {remaining_seconds // 60}m {remaining_seconds % 60}s"
                remaining_time_str = remaining_time_str.ljust(30)  # Adjust the number 30 according to the maximum expected length of the string
                print(remaining_time_str, end="\r")
                time.sleep(1)

            print("Checking for trades now...\n")
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    main()
    print("Press Enter to exit.")
    input()


    
