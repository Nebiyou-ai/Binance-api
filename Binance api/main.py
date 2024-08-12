import threading
import pandas as pd
from time import sleep
import ta
from strategy import TrendFollowingStrategy
from binance.error import ClientError
from binance.exceptions import BinanceAPIException, BinanceOrderException
from binance1 import Binance
from backtest import profitable_symbols
from datetime import datetime, timedelta

# Initialize indicator periods
ema_period = 5
sma_period = 10
rsi_period = 14
bb_period = 20
macd_fast_period = 12
macd_slow_period = 26
macd_signal_period = 9
atr_period = 14

# Dictionary to keep track of last check time for each symbol
last_check_time = {}

def get_realtime_data(binance_client, symbol, timeframe):
    try:
        df = binance_client.klines(symbol, timeframe)
        df = pd.DataFrame(df)
        df = df.iloc[:, :6]
        df.columns = ['Time', 'Open', 'High', 'Low', 'Close']
        df = df.set_index('Time')
        df.index = pd.to_datetime(df.index, unit='ms')
        df = df.astype(float)
        return df
    except ClientError as e:
        print(f"Error fetching real-time data: {e}")
        return None

def check_current_conditions(df):
    # Calculate indicators
    df['EMA'] = ta.trend.EMAIndicator(close=df['Close'], window=ema_period).ema_indicator()
    df['SMA'] = ta.trend.SMAIndicator(close=df['Close'], window=sma_period).sma_indicator()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=rsi_period).rsi()
    bb = ta.volatility.BollingerBands(close=df['Close'], window=bb_period)
    df['UpperBB'] = bb.bollinger_hband()
    df['LowerBB'] = bb.bollinger_lband()
    macd = ta.trend.MACD(close=df['Close'], window_fast=macd_fast_period, window_slow=macd_slow_period, window_sign=macd_signal_period)
    df['MACD'] = macd.macd()
    df['MACDSignal'] = macd.macd_signal()
    df['ATR'] = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=atr_period).average_true_range()

    # Example conditions
    latest_close = df['Close'].iloc[-1]
    latest_ema = df['EMA'].iloc[-1]
    latest_rsi = df['RSI'].iloc[-1]
    latest_macd = df['MACD'].iloc[-1]
    latest_macd_signal = df['MACDSignal'].iloc[-1]

    # Example condition: Close < EMA, RSI < 40
    if latest_close < latest_ema and latest_rsi < 40:
        return 'BUY'
    elif latest_close > latest_ema and latest_rsi > 60:
        return 'SELL'
    else:
        return None

def live_trade(binance_client, symbol, strategy):
    df = get_realtime_data(binance_client, symbol, '5m')
    if df is None:
        print(f"Failed to get real-time data for {symbol}.")
        return

    # Ensure the data is sorted
    df.sort_index(inplace=True)

    # Check the current conditions
    trade_signal = check_current_conditions(df)
    if trade_signal:
        print(f"Trade signal for {symbol}: {trade_signal}")
        # Retrieve balance
        balance = binance_client.get_balance_usdt()
        if balance is None:
            print("Unable to fetch balance.")
            return

        # Example trading parameters
        volume = 5  # Adjust volume as needed (this is the capital you want to invest)
        leverage = 2
        mode = 'ISOLATED'
        tp_percentage = 0.03  # 3% take profit
        sl_percentage = 0.01  # 1% stop loss
        limit_offset = 0.01  # 1% below/above the current price for limit orders

        # Fetch the current price
        price = float(binance_client.client.ticker_price(symbol)['price'])
        print(f"Current price for {symbol}: {price}")

        # Calculate TP and SL prices
        if trade_signal == 'BUY':
            tp_price = price * (1 + tp_percentage)
            sl_price = price * (1 - sl_percentage)
        elif trade_signal == 'SELL':
            tp_price = price * (1 - tp_percentage)
            sl_price = price * (1 + sl_percentage)
        
        print(f"Calculated Take Profit (TP) price: {tp_price}")
        print(f"Calculated Stop Loss (SL) price: {sl_price}")

        qty_precision, price_precision = binance_client.get_precisions(symbol)
        qty = round(volume / price, qty_precision)

        # Calculate the amount invested and required balance
        amount_invested = volume / leverage
        balance_without_leverage = qty * price

        print(f"Amount to be invested for {symbol} with {leverage}x leverage: {amount_invested:.2f} USDT")
        print(f"Balance required without leverage: {balance_without_leverage:.2f} USDT")

        if balance >= amount_invested:
            try:
                # Display the amount before placing the order
                print(f"Placing order for {symbol}...")
                print(f"Capital required before placing order: {amount_invested:.2f} USDT")
                
                response = binance_client.futures_create_order(
                    symbol=symbol,
                    side=trade_signal,
                    volume=volume,
                    leverage=leverage,
                    mode=mode,
                    tp=tp_percentage,
                    sl=sl_percentage,
                    limit_offset=limit_offset
                )
                print(f"Order placed for {symbol} as {trade_signal}. Response: {response}")

                # Verify if the order is in the system
                open_orders = binance_client.check_orders()
                if any(order['symbol'] == symbol for order in open_orders):
                    print(f"Order successfully placed and is active for {symbol}.")
                else:
                    print(f"Order for {symbol} might not have been placed correctly.")

                # Fetch and display remaining balance
                remaining_balance = binance_client.get_balance_usdt()
                print(f"Remaining futures balance after placing order: {remaining_balance:.2f} USDT")
                
            except (BinanceAPIException, BinanceOrderException) as e:
                print(f"Error placing order for {symbol}: {e}")
        else:
            print(f"Insufficient funds to place order for {symbol}. Required: {amount_invested:.2f} USDT, Available: {balance:.2f} USDT.")
    else:
        print(f"No trade conditions met for {symbol}. Waiting for 2 minutes before rechecking.")

def live_trading_loop():
    binance_client = Binance()
    
    while True:
        if profitable_symbols:
            now = datetime.now()
            for symbol in profitable_symbols:
                # Check if it's time to check this symbol
                if symbol in last_check_time:
                    last_time = last_check_time[symbol]
                    if now < last_time + timedelta(minutes=2):
                        continue  # Skip if it's not yet time to check again

                # Update the last check time for this symbol
                last_check_time[symbol] = now
                
                # Manage open positions
                open_positions = binance_client.get_positions()
                if symbol in open_positions:
                    print(f"Position already open for {symbol}.")
                    continue

                # Close open orders for the symbol
                open_orders = binance_client.check_orders()
                if symbol in open_orders:
                    binance_client.close_open_orders(symbol)
                
                live_trade(binance_client, symbol, TrendFollowingStrategy)
                
                print(f"Waiting before next symbol...")
                sleep(1)  # Short sleep to avoid tight loop, adjust as needed
        else:
            print("No profitable symbols to trade. Waiting for backtest to update...")
            sleep(10)  # Check for updates every 10 seconds

# Start the live trading loop in a separate thread
live_trading_thread = threading.Thread(target=live_trading_loop)
live_trading_thread.start()