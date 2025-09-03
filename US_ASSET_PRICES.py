import os, json, time, math
from typing import List, Dict
from datetime import date
from API_Keys import API_KEY, API_SECRET, PAPER

# ---------- Alpaca SDK ----------
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass
from alpaca.data import (
    StockHistoricalDataClient,
    StockLatestQuoteRequest,
    StockLatestTradeRequest,
)
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# IEX is the only feed on free plan (don’t change this to "sip" unless you have access)
DATA_FEED = "iex"

# Universe filters
EXCHANGES  = {"NYSE", "NASDAQ", "ARCA"}  # ignore OTC/OTCBB etc. (often sparse)
BATCH_SIZE = 200
SLEEP_SEC  = 0.20      # safety between batches
RETRIES    = 2         # simple retry count for transient errors

# ---------- Helpers ----------
def chunked(seq: List[str], n: int):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0

# ---------- Clients ----------
trading = TradingClient(API_KEY, API_SECRET, paper = PAPER)
data    = StockHistoricalDataClient(API_KEY, API_SECRET)
acct = trading.get_account()

# ---------- Build Universe ----------
search_params = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
assets = trading.get_all_assets(search_params)
symbols = [
    a.symbol
    for a in assets
    if getattr(a, "tradable", False)
    and getattr(a, "status", "active") == "active"
    and getattr(a, "exchange", "") in EXCHANGES
]
symbols = sorted(set(symbols))

print(f"Universe size: {len(symbols)} symbols")

# ---------- Collect Prices ----------
prices: Dict[str, float] = {}
missing_for_bars: List[str] = []

def fetch_batch(batch_syms: List[str]):
    # latest trade + quote
    q_req = StockLatestQuoteRequest(symbol_or_symbols=batch_syms, feed=DATA_FEED)
    t_req = StockLatestTradeRequest(symbol_or_symbols=batch_syms, feed=DATA_FEED)

    quotes = data.get_stock_latest_quote(q_req)   # dict-like: sym -> Quote
    trades = data.get_stock_latest_trade(t_req)   # dict-like: sym -> Trade

    # resolve price
    mfb_local: List[str] = []
    for sym in batch_syms:
        price = None

        # 1) latest trade
        tr = trades.get(sym)
        if tr:
            tp = safe_float(getattr(tr, "price", 0.0))
            if tp > 0:
                price = tp

        # 2) quote mid / ask / bid
        if price is None:
            q = quotes.get(sym)
            if q:
                bid = safe_float(getattr(q, "bid_price", 0.0))
                ask = safe_float(getattr(q, "ask_price", 0.0))
                if bid > 0 and ask > 0:
                    price = (bid + ask) / 2.0
                elif ask > 0:
                    price = ask
                elif bid > 0:
                    price = bid

        # 3) if still missing, mark for previous close
        if price is None:
            mfb_local.append(sym)
        else:
            prices[sym] = float(price)

    return mfb_local

def fetch_prev_close_bar(missing_syms: List[str]):
    """Fill prices with the most recent daily close for symbols that
    couldn't be priced via latest trade/quote.

    Note: alpaca-py returns a Bars object (a BarSet) from get_stock_bars,
    whose symbol→list[Bar] mapping lives under .data. Don't call dict
    methods like .get() directly on the Bars object.
    """   # ✅ added docstring for clarity

    if not missing_syms:
        return

    bar_req = StockBarsRequest(
        symbol_or_symbols=missing_syms,
        timeframe=TimeFrame.Day,
        limit=1,
        feed=DATA_FEED,
    )   # ✅ minor style (trailing comma, reformatting)

    bars = data.get_stock_bars(bar_req)  # Bars (aka BarSet)   # ✅ updated comment
    symbol_to_bars = getattr(bars, "data", {})  # Dict[str, List[Bar]]   # ✅ NEW LINE

    for sym in missing_syms:
        blist = symbol_to_bars.get(sym, []) if isinstance(symbol_to_bars, dict) else []   # ✅ UPDATED LINE
        if blist:
            prices[sym] = float(getattr(blist[0], "close", 0.0))
        else:
            # final fallback if absolutely nothing
            prices.setdefault(sym, None)

# Main loop with simple retries
for batch in chunked(symbols, BATCH_SIZE):
    attempt = 0
    while True:
        try:
            pending = fetch_batch(batch)
            # collect for bars (we’ll do one bars call per batch after batch resolution)
            missing_for_bars.extend(pending)
            break
        except Exception as e:
            attempt += 1
            if attempt > RETRIES:
                print(f"[WARN] Batch failed after retries: {e}")
                # mark all as missing so we at least try bars
                missing_for_bars.extend(batch)
                break
            time.sleep(0.5)

    time.sleep(SLEEP_SEC)

# Fetch previous close for anything we couldn’t resolve live
for batch in chunked(missing_for_bars, BATCH_SIZE):
    attempt = 0
    while True:
        try:
            fetch_prev_close_bar(batch)
            break
        except Exception as e:
            attempt += 1
            if attempt > RETRIES:
                print(f"[WARN] Bars fetch failed after retries: {e}")
                for sym in batch:
                    prices.setdefault(sym, 0.0)
                break
            time.sleep(0.5)
    time.sleep(SLEEP_SEC)

# ---------- Save ----------
file_path = f"US_ASSET_PRICES/{date.today()}_US_ASSET_PRICES.json"
with open(file_path, "w") as f:
    json.dump(prices, f, indent=2)

print(f"Saved {len(prices)} symbols to {file_path}")
