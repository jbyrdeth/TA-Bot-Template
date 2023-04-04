import ccxt
import numpy as np
import pandas as pd
import talib
import time
from itertools import product

api_key = 'YOUR API KEY'
secret_key = 'YOUR SECRET API KEY'

binance = ccxt.binanceus({
    "apiKey": api_key,
    "secret": secret_key,
    "enableRateLimit": True
})

symbols = ["ETH/USD"]

# Define the parameter ranges to test
rsi_threshold_range = [40, 50, 60]
ema_timeperiod_range = [(10, 20), (20, 50), (50, 100)]
bb_timeperiod_range = [(20, 2), (30, 2), (40, 2)]

# Define the timeframe combinations to test
timeframe_combinations = [("5m", "15m", "1h"), ("1h", "4h", "1d")]

# Define the start and end dates for the backtest
start_date = '2023-03-20'
end_date = '2023-04-03'


def fetch_data(symbol, timeframe, start_date, end_date):
    since = int(pd.Timestamp(start_date).timestamp() * 1000)
    now = int(pd.Timestamp(end_date).timestamp() * 1000)
    data = []
    while since < now:
        new_data = binance.fetch_ohlcv(symbol, timeframe, limit=1000, since=since)
        if not new_data:
            break
        data.extend(new_data)
        since = data[-1][0]
        time.sleep(binance.rateLimit / 1000)
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def add_indicators(df, ema_timeperiods, bb_timeperiods):
    df["20_EMA"] = talib.EMA(df["close"], timeperiod=ema_timeperiods[0])
    df["50_EMA"] = talib.EMA(df["close"], timeperiod=ema_timeperiods[1])
    df["RSI"] = talib.RSI(df["close"], timeperiod=14)
    df["BB_upper"], df["BB_middle"], df["BB_lower"] = talib.BBANDS(df["close"], timeperiod=bb_timeperiods[0], nbdevup=bb_timeperiods[1], nbdevdn=bb_timeperiods[1])
    
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


def check_entry_conditions_long(df_5m, df_15m, df_1h, rsi_threshold):
    if (
        df_5m["close"].iloc[-1] > df_5m["20_EMA"].iloc[-1]
        and df_5m["RSI"].iloc[-1] > rsi_threshold
        and df_15m["close"].iloc[-1] > df_15m["BB_middle"].iloc[-1]
        and df_1h["close"].iloc[-1] > df_1h["Ichimoku_cloud_top"].iloc[-1]
    ):
        return True
    return False
    

def check_entry_conditions_short(df_5m, df_15m, df_1h, rsi_threshold):
    if (
        df_5m["close"].iloc[-1] < df_5m["20_EMA"].iloc[-1]
        and df_5m["RSI"].iloc[-1] < rsi_threshold
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


def backtest_strategy(strategy_function, df_5m, df_15m, df_1h, rsi_threshold, ema_timeperiods, bb_timeperiods):
    # Define an empty list to store trade results
    trades = []
    df = df_5m
    
    # Define an empty list to store trade results
    trades = []
    
    print("Running backtest strategy...")
    
    # Iterate through the DataFrame
    for i in range(len(df)):
        # Execute the strategy function and get the trade result
        trade = strategy_function(df_5m.iloc[:i+1], df_15m.iloc[:i+1], df_1h.iloc[:i+1], rsi_threshold, ema_timeperiods, bb_timeperiods)

        if trade:
            trades.append(trade)
    
    print("Backtest strategy complete.")
    
    return trades


def long_strategy(df_5m, df_15m, df_1h, rsi_threshold, ema_timeperiods, bb_timeperiods):
    if check_entry_conditions_long(df_5m, df_15m, df_1h, rsi_threshold):
        print("Long strategy: Entry conditions met.")
        
        entry_price = df_5m["close"].iloc[-1] # Change here
        stop_loss = df_5m["low"].rolling(window=5).min().iloc[-1] # Change here
        take_profit = fibonacci_extensions(df_5m)[0] # Change here

        trade_result = {
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "profit": take_profit - entry_price
        }
        
        return trade_result
    else:
        return None


def short_strategy(df_5m, df_15m, df_1h, rsi_threshold, ema_timeperiods, bb_timeperiods):
    if check_entry_conditions_short(df_5m, df_15m, df_1h, rsi_threshold):
        print("Short strategy: Entry conditions met.")
        
        entry_price = df_5m["close"].iloc[-1] # Change here
        stop_loss = df_5m["high"].rolling(window=5).max().iloc[-1] # Change here
        take_profit = fibonacci_retracements(df_5m)[0] # Change here

        trade_result = {
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "profit": entry_price - take_profit
        }
        
        return trade_result
    else:
        return None



def main():
    try:
        print("Start of main function")
        input("Press Enter to continue...")

        results = []

        # Iterate through all parameter combinations
        for i, (rsi_threshold, ema_timeperiods, bb_timeperiods) in enumerate(product(rsi_threshold_range, ema_timeperiod_range, bb_timeperiod_range)):
            print(f"Parameter combination {i + 1}: RSI: {rsi_threshold}, EMA: {ema_timeperiods}, BB: {bb_timeperiods}")

            for timeframe_combination in timeframe_combinations:
                print(f"Timeframe combination: {timeframe_combination}")

                for symbol in symbols:
                    print(f"Fetching data for {symbol}")

                    # Fetch data for each timeframe
                    df_5m = fetch_data(symbol, timeframe_combination[0], start_date, end_date)
                    print(f"Fetched 5m data for {symbol}")
                    df_15m = fetch_data(symbol, timeframe_combination[1], start_date, end_date)
                    print(f"Fetched 15m data for {symbol}")
                    df_1h = fetch_data(symbol, timeframe_combination[2], start_date, end_date)
                    print(f"Fetched 1h data for {symbol}")

                    # Backtest long and short strategies
                    print("Backtesting long and short strategies")
                    input("Press Enter to continue...")
                    long_trades = backtest_strategy(long_strategy, df_5m, df_15m, df_1h, rsi_threshold, ema_timeperiods, bb_timeperiods)
                    short_trades = backtest_strategy(short_strategy, df_5m, df_15m, df_1h, rsi_threshold, ema_timeperiods, bb_timeperiods)
                    print(f"Backtests completed for {symbol} with RSI: {rsi_threshold}, EMA: {ema_timeperiods}, BB: {bb_timeperiods}")

                    # Calculate metrics
                    total_trades = len(long_trades) + len(short_trades)
                    total_profit = sum([trade["profit"] for trade in long_trades]) + sum([trade["profit"] for trade in short_trades])

                    results.append({
                        "symbol": symbol,
                        "timeframe_combination": timeframe_combination,
                        "rsi_threshold": rsi_threshold,
                        "ema_timeperiods": ema_timeperiods,
                        "bb_timeperiods": bb_timeperiods,
                        "total_trades": total_trades,
                        "total_profit": total_profit
                    })

        # Find the best parameter combination
        best_result = max(results, key=lambda x: x["total_profit"])
        print("Best parameter combination:", best_result)
    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    main()


