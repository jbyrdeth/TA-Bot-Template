import time
import ccxt
import pandas as pd
import numpy as np
import talib
import datetime

api_key = 'YOUR API KEY'
api_secret = 'YOUR SECRET API KEY'

exchange = ccxt.binanceus({
    'apiKey': api_key,
    'secret': api_secret,
})

symbol = 'MATIC/USD'
timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '6h', '1d']

def fetch_ohlcv_data(symbol, timeframe):
    data = exchange.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def sma_analysis(df):
    sma50 = talib.SMA(df['close'], timeperiod=50)
    sma200 = talib.SMA(df['close'], timeperiod=200)
    return sma50, sma200

def rsi_analysis(df):
    rsi = talib.RSI(df['close'], timeperiod=14)
    return rsi

def bb_analysis(df):
    bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
    return bb_upper, bb_middle, bb_lower

def macd_analysis(df):
    macd, macdsignal, macdhist = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
    return macd, macdsignal, macdhist

def generate_signal(df):
    sma50, sma200 = sma_analysis(df)
    rsi = rsi_analysis(df)
    bb_upper, bb_middle, bb_lower = bb_analysis(df)
    macd, macdsignal, macdhist = macd_analysis(df)

    # Calculate the score for each indicator
    sma50_score = np.where(df['close'] > sma50, 1, -1).sum()
    sma200_score = np.where(df['close'] > sma200, 1, -1).sum()
    rsi_score = np.where(rsi > 50, 1, -1).sum()
    bb_score = np.where(df['close'] > bb_middle, 1, -1).sum()
    macd_score = np.where(macdhist > 0, 1, -1).sum()

    # Combine the scores for each indicator
    score = sma50_score + sma200_score + rsi_score + bb_score + macd_score

    # Generate long or short suggestion based on the combined score
    if score > 0:
        long = True
        short = False
    elif score < 0:
        long = False
        short = True
    else:
        long = False
        short = False

    # Generate target price and stop loss for the position
    if long:
        entry_price = df['close'].iloc[-1]
        target_price = entry_price * 1.02
        stop_loss = entry_price * 0.98
    elif short:
        entry_price = df['close'].iloc[-1]
        target_price = entry_price * 0.98
        stop_loss = entry_price * 1.02
    else:
        entry_price = None
        target_price = None
        stop_loss = None

    confidence = calculate_confidence(df, sma50, sma200, rsi, bb_upper, bb_middle, bb_lower, macdhist)

    return long, short, entry_price, target_price, stop_loss, confidence
def calculate_confidence(df, sma50, sma200, rsi, bb_upper, bb_middle, bb_lower, macdhist):
    sma50_confidence = (df['close'].iloc[-1] / sma50.iloc[-1] - 1) * 100
    sma200_confidence = (df['close'].iloc[-1] / sma200.iloc[-1] - 1) * 100
    rsi_confidence = (rsi.iloc[-1] / 50 - 1) * 100
    bb_confidence = (df['close'].iloc[-1] / bb_middle.iloc[-1] - 1) * 100
    macd_confidence = (macdhist.iloc[-1] / np.abs(macdhist).mean() - 1) * 100

    confidence = (sma50_confidence + sma200_confidence + rsi_confidence + bb_confidence + macd_confidence) / 5
    return np.clip(confidence, 0, 100)

while True:
    current_time = datetime.datetime.now()
    print(f'[{current_time}] Checking trade positions:')
    for timeframe in timeframes:
        df = fetch_ohlcv_data(symbol, timeframe)
        long, short, entry_price, target_price, stop_loss, confidence = generate_signal(df)

        if long:
            print(f'{timeframe} LONG position: Entry Price {entry_price}, Target Price {target_price}, Stop Loss {stop_loss}, Confidence {confidence:.2f}%')
        elif short:
            print(f'{timeframe} SHORT position: Entry Price {entry_price}, Target Price {target_price}, Stop Loss {stop_loss}, Confidence {confidence:.2f}%')
        else:
            print(f'{timeframe}: No clear signal. Confidence {confidence:.2f}%')


    # Calculate the remaining time until the next iteration
    remaining_seconds = 60 - datetime.datetime.now().second
    print(f'Next check in {remaining_seconds} seconds.\n')

    # Countdown timer
    for i in range(remaining_seconds, 0, -1):
        print(f'{i} seconds remaining.', end='\r')
        time.sleep(1)
    print('\n')  # Add a blank line between iterations
