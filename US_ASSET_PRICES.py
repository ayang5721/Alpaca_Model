import os, json
import datetime
import sys
import time
from datetime import date
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetAssetsRequest
from alpaca.trading.enums import OrderSide, TimeInForce, AssetClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient

from API_Keys import API_KEY, API_SECRET, PAPER

trading_client = TradingClient(API_KEY, API_SECRET, paper=PAPER)
search_params = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
assets = trading_client.get_all_assets(search_params)

symbols = [a.symbol for a in assets if a.tradable and a.exchange in ["NASDAQ", "NYSE", "ARCA"]]

data_client = StockHistoricalDataClient(API_KEY, API_SECRET)

def chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

stock_prices = {}

for batch in chunks(symbols, 200):  # batch size 200
    req = StockLatestQuoteRequest(symbol_or_symbols=batch)
    quotes = data_client.get_stock_latest_quote(req)

    for sym in batch:
        if sym in quotes:
            stock_prices[sym] = quotes[sym].ask_price

    time.sleep(0.2)  # rate-limit safety

stock_prices = {"date": str(date.today()), **stock_prices}

file_path = f"US_ASSET_PRICES/{date.today()}_US_ASSET_PRICES.json"
with open(file_path, "w") as f:
    json.dump(stock_prices, f, indent=4)

print(f"Saved {len(stock_prices)} symbols to us_stock_prices.json")
