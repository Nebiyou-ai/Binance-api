import threading
from backtest import backtesting_loop
backtesting_thread = threading.Thread(target=backtesting_loop)
backtesting_thread.start()
from binance.error import ClientError
import pandas as pd
from time import sleep
from binance.um_futures import UMFutures
from config import API_KEY, API_SECRET

class Binance:
    def __init__(self):
        self.api = API_KEY
        self.secret = API_SECRET
        self.client = UMFutures(key=self.api, secret=self.secret)

    def get_balance_usdt(self):
        try:
            response = self.client.balance(recvWindow=10000)
            for elem in response:
                if elem['asset'] == 'USDT':
                    return float(elem['balance'])
        except ClientError as error:
            print(f"Error fetching balance: {error}")

    def get_positions(self):
        try:
            resp = self.client.get_position_risk(recvWindow=10000)
            pos = []
            for elem in resp:
                if float(elem['positionAmt']) != 0:
                    pos.append(elem['symbol'])
            return pos
        except ClientError as error:
            print(f"Error fetching positions: {error}")

    def check_orders(self):
        try:
            response = self.client.get_orders(recvWindow=10000)
            sym = []
            for elem in response:
                sym.append(elem['symbol'])
            return sym
        except ClientError as error:
            print(f"Error fetching orders: {error}")

    def close_open_orders(self, symbol):
        try:
            response = self.client.cancel_open_orders(symbol=symbol, recvWindow=10000)
            print(f"Closed orders: {response}")
        except ClientError as error:
            print(f"Error closing orders: {error}")

    def get_tickers_usdt(self):
        try:
            tickers = []
            resp = self.client.ticker_price()
            for elem in resp:
                if 'USDT' in elem['symbol']:
                    tickers.append(elem['symbol'])
            return tickers
        except ClientError as error:
            print(f"Error fetching tickers: {error}")

    def get_pnl(self, limit):
        try:
            resp = self.client.get_income_history(incomeType="REALIZED_PNL", limit=limit, recvWindow=10000)[::-1]
            pnl = 0
            for elem in resp:
                pnl += float(elem['income'])
            return pnl
        except ClientError as error:
            print(f"Error fetching PnL: {error}")

    def klines(self, symbol, timeframe):
        try:
            resp = pd.DataFrame(self.client.klines(symbol, timeframe, recvWindow=10000))
            resp = resp.iloc[:, :6]
            resp.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            resp = resp.set_index('Time')
            resp.index = pd.to_datetime(resp.index, unit='ms')
            resp = resp.astype(float)
            return resp
        except ClientError as error:
            print(f"Error fetching klines: {error}")

    def set_leverage(self, symbol, level):
        try:
            response = self.client.change_leverage(symbol=symbol, leverage=level, recvWindow=10000)
            print(f"Set leverage: {response}")
        except ClientError as error:
            print(f"Error setting leverage: {error}")

    def set_mode(self, symbol, margin_type):
        try:
            response = self.client.change_margin_type(symbol=symbol, marginType=margin_type, recvWindow=10000)
            print(f"Set margin type: {response}")
        except ClientError as error:
            print(f"Error setting margin type: {error}")

    def get_precisions(self, symbol):
        try:
            resp = self.client.exchange_info()['symbols']
            for elem in resp:
                if elem['symbol'] == symbol:
                    return elem['pricePrecision'], elem['quantityPrecision']
            raise ValueError(f"Symbol {symbol} not found in exchange info.")
        except ClientError as error:
            print(f"Error fetching precisions: {error}")
            raise
        except ValueError as error:
            print(f"Error: {error}")
            raise

    def get_commission(self, symbol):
        try:
            resp = self.client.commission_rate(symbol=symbol, recvWindow=10000)
            return float(resp['makerCommissionRate']), float(resp['takerCommissionRate'])
        except ClientError as error:
            print(f"Error fetching commission: {error}")

    def futures_create_order(self, symbol, side, volume, leverage, mode, tp, sl, limit_offset):
        self.set_leverage(symbol, leverage)
        self.set_mode(symbol, mode)
        price = float(self.client.ticker_price(symbol)['price'])
        qty_precision, price_precision = self.get_precisions(symbol)
        qty = round(volume / price, qty_precision)

        if side == 'buy':
            limit_price = round(price * (1 - limit_offset), price_precision)
            try:
                resp1 = self.client.new_order(
                    symbol=symbol,
                    side='BUY',
                    type='LIMIT',
                    quantity=qty,
                    price=limit_price,
                    timeInForce='GTC',
                    recvWindow=10000
                )
                print(f"Buy limit order: {resp1}")
                sleep(1)
                sl_price = round(limit_price - limit_price * sl, price_precision)
                resp2 = self.client.new_order(
                    symbol=symbol,
                    side='SELL',
                    type='STOP_MARKET',
                    quantity=qty,
                    stopPrice=sl_price,
                    closePosition="true",
                    workingType="MARK_PRICE",
                    recvWindow=10000
                )
                print(f"Stop loss order: {resp2}")
                sleep(1)
                tp_price = round(limit_price + limit_price * tp, price_precision)
                resp3 = self.client.new_order(
                    symbol=symbol,
                    side='SELL',
                    type='TAKE_PROFIT_MARKET',
                    quantity=qty,
                    stopPrice=tp_price,
                    closePosition="true",
                    workingType="MARK_PRICE",
                    recvWindow=10000
                )
                print(f"Take profit order: {resp3}")
            except ClientError as error:
                print(f"Error executing buy limit order: {error}")

        elif side == 'sell':
            limit_price = round(price * (1 + limit_offset), price_precision)
            try:
                resp1 = self.client.new_order(
                    symbol=symbol,
                    side='SELL',
                    type='LIMIT',
                    quantity=qty,
                    price=limit_price,
                    timeInForce='GTC',
                    recvWindow=10000
                )
                print(f"Sell limit order: {resp1}")
                sleep(1)
                sl_price = round(limit_price + limit_price * sl, price_precision)
                resp2 = self.client.new_order(
                    symbol=symbol,
                    side='BUY',
                    type='STOP_MARKET',
                    quantity=qty,
                    stopPrice=sl_price,
                    closePosition="true",
                    workingType="MARK_PRICE",
                    recvWindow=10000
                )
                print(f"Stop loss order: {resp2}")
                sleep(1)
                tp_price = round(limit_price - limit_price * tp, price_precision)
                resp3 = self.client.new_order(
                    symbol=symbol,
                    side='BUY',
                    type='TAKE_PROFIT_MARKET',
                    quantity=qty,
                    stopPrice=tp_price,
                    closePosition="true",
                    workingType="MARK_PRICE",
                    recvWindow=10000
                )
                print(f"Take profit order: {resp3}")
            except ClientError as error:
                print(f"Error executing sell limit order: {error}")  