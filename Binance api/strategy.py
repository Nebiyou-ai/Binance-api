from backtesting import Strategy
import ta
import pandas as pd

# Define indicator functions
def ema(df, period=5):
    return ta.trend.EMAIndicator(close=df['Close'], window=period).ema_indicator()

def sma(df, period=10):
    return ta.trend.SMAIndicator(close=df['Close'], window=period).sma_indicator()

def rsi(df, period=14):
    return ta.momentum.RSIIndicator(close=df['Close'], window=period).rsi()

def bollinger_bands(df, period=20):
    bb = ta.volatility.BollingerBands(close=df['Close'], window=period)
    return bb.bollinger_hband(), bb.bollinger_lband()

def macd(df, fast_period=12, slow_period=26, signal_period=9):
    macd = ta.trend.MACD(close=df['Close'], window_slow=slow_period, window_fast=fast_period, window_sign=signal_period)
    return macd.macd(), macd.macd_signal()

def atr(df, period=14):
    atr = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=period)
    return atr.average_true_range()

class TrendFollowingStrategy(Strategy):
    ema_period = 5
    sma_period = 10
    rsi_period = 14
    bb_period = 20
    macd_fast_period = 12
    macd_slow_period = 26
    macd_signal_period = 9
    atr_period = 14 #atr supposed to be 1.5

    def init(self):
        # Initialize indicators
        self.ema = self.I(ema, self.data.df, self.ema_period)
        self.sma = self.I(sma, self.data.df, self.sma_period)
        self.rsi = self.I(rsi, self.data.df, self.rsi_period)
        self.bb_hband, self.bb_lband = self.I(bollinger_bands, self.data.df, self.bb_period)
        self.macd, self.macd_signal = self.I(macd, self.data.df, self.macd_fast_period, self.macd_slow_period, self.macd_signal_period)
        self.atr = self.I(atr, self.data.df, self.atr_period)

    def next(self):
        price = self.data.Close[-1]
        rsi_value = self.rsi[-1]
        slippage_pct = 0.0002  # 0.02% slippage

        # Check for buy signal
        if (self.data.Close[-1] < self.ema[-1] and rsi_value < 40):
            if not self.position:
                buy_price = price * (1 + slippage_pct)  # Add slippage to buy price
                take_profit = buy_price * 1.03  # TP is 3% above buy price
                stop_loss = buy_price * 0.99  # SL is 1% below buy price
                self.buy(size=0.02, tp=take_profit, sl=stop_loss)

        # Check for sell signal
        if (self.data.Close[-1] > self.ema[-1] and rsi_value > 60):
            if self.position:
                sell_price = price * (1 - slippage_pct)  # Subtract slippage from sell price
                take_profit = sell_price * 0.97  # TP is 3% below sell price
                stop_loss = sell_price * 1.01  # SL is 1% above sell price
                self.sell(size=0.02, tp=take_profit, sl=stop_loss)