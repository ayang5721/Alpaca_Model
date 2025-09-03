import os

API_KEY    = os.environ["ALPACA_API_KEY"]
API_SECRET = os.environ["ALPACA_API_SECRET"]
PAPER      = os.environ.get("ALPACA_PAPER", "true").lower() == "true"