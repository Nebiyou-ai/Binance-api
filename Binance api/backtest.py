from time import time, sleep
from backtesting import Backtest
from helper import get_tickers_usdt, klines_extended
from strategy import TrendFollowingStrategy
import threading

# Define slippage
slippage_pct = 0.0002  # 0.02% slippage

# Define timeframe and interval
timeframe = '5m'
interval = 30

# Define the sleep time in seconds (e.g., 24 hours)
sleep_time = 24 * 60 * 60

# Fetch ticker symbols
symbols = get_tickers_usdt()
profitable_symbols = []

def backtesting_loop():
    global profitable_symbols
    while True:
        profitable_symbols.clear()  # Clear previous results

        for symbol in symbols:
            # Fetch historical data
            kl = klines_extended(symbol, timeframe, interval)
            
            # Perform backtest
            bt = Backtest(kl, TrendFollowingStrategy, cash=1000, margin=1/10, commission=0.0007)
            stats = bt.run()
            
            # Check if the symbol is profitable
            if stats['Return [%]'] > 1:
                profitable_symbols.append(symbol)
                print(f"Results for {symbol}:")
                print(f"{'Start:':<20} {stats['Start']}")
                print(f"{'End:':<20} {stats['End']}")
                print(f"{'Equity Final [$]:':<20} {stats['Equity Final [$]']:.2f}")
                print(f"{'Equity Peak [$]:':<20} {stats['Equity Peak [$]']:.2f}")
                print(f"{'# Trades:':<20} {stats['# Trades']}")
                print(f"{'Return [%]:':<20} {stats['Return [%]']:.2f}")
                print(f"{'Win Rate [%]:':<20} {stats['Win Rate [%]']:.2f}")
                print(f"{'Profit Factor:':<20} {stats['Profit Factor']:.2f}")
                print(f"{'Expectancy [%]:':<20} {stats['Expectancy [%]']:.2f}")
                print(f"{'SQN:':<20} {stats['SQN']:.2f}")
                print("----")
            else:
                print(f"Symbol {symbol} was not profitable.")

        # Print the list of profitable symbols after each loop iteration
        print(f"Profitable symbols: {profitable_symbols}")

        # Sleep for the specified time before the next iteration
        sleep(sleep_time)

# Start the backtesting loop in a separate thread
backtesting_thread = threading.Thread(target=backtesting_loop)
backtesting_thread.start()
