import os, json
import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetAssetsRequest
from alpaca.trading.enums import OrderSide, TimeInForce, AssetClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

#API Keys
API_KEY    = os.environ["ALPACA_API_KEY"]
API_SECRET = os.environ["ALPACA_API_SECRET"]
PAPER      = os.environ.get("ALPACA_PAPER", "true").lower() == "true"

#Clients - trading and stock information/data
trading_client = TradingClient(API_KEY, API_SECRET, paper=PAPER)
data_client = StockHistoricalDataClient(API_KEY, API_SECRET)

#Trading/market testing (no orders)
acct = trading_client.get_account()
print("Status:", acct.status, "| Buying power:", acct.buying_power)
print("Blocked Status: ", acct.trading_blocked)

print(f"Balance calc: {float(acct.equity)} - {float(acct.last_equity)} = ", float(acct.equity) - float(acct.last_equity))

search_params = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
assets = trading_client.get_all_assets(search_params)

aapl_asset = trading_client.get_asset("AAPL")
print("AAPL Asset:", aapl_asset)
print("APPL TRADE STATUS:", aapl_asset.tradable)

file_name = "US_ASSET_DATA/8_27_US_ASSETS.json"
if not os.path.exists(file_name):
    with open (file_name, "w") as f:
        json.dump(assets, f, indent=4, default=str)
    
#Stock information testing (specific stock data)
request_params = StockLatestQuoteRequest(symbol_or_symbols="AAPL")
quote = data_client.get_stock_latest_quote(request_params)

print("AAPL CURRENT PRICE:", quote["AAPL"].ask_price)

start = datetime.datetime(2023, 1, 4)
end = datetime.datetime(2023, 6, 4)

request_params = StockBarsRequest(
    symbol_or_symbols=["AAPL"],
    timeframe=TimeFrame.Month,
    start=start,
    end=end
)

bars = data_client.get_stock_bars(request_params)

for bar in bars.data["AAPL"]:
    print(f"Date: {bar.timestamp}, Open: {bar.open}, Close: {bar.close}")
