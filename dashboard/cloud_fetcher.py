"""
Cloud Mode — fetches prices directly from exchange REST APIs.
Used when USE_KAFKA=false (e.g. Streamlit Community Cloud deployment).

No Kafka broker required. Prices are cached for 8 seconds to avoid
hammering the exchange APIs on every Streamlit rerun.
"""

import time
from collections import deque

import requests
import streamlit as st

from config import SYMBOLS, ARBITRAGE_THRESHOLD_PCT

# Module-level alert store — shared across all Streamlit sessions
# in the same process (good enough for a public demo)
_alerts: deque = deque(maxlen=50)
_last_alert_key: str = ""  # prevents duplicate alerts within 30 s


# ── Price fetching (cached 8 s) ────────────────────────────────────────────────

@st.cache_data(ttl=8)
def fetch_prices() -> dict:
    """
    Returns: {symbol: {exchange: price_float}}
    Fetches from Binance, Coinbase, Kraken in parallel-ish (sequential but fast).
    """
    prices: dict = {}

    # Binance — symbol format: BTCUSDT
    for symbol in SYMBOLS:
        try:
            resp = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": symbol.replace("/", "")},
                timeout=5,
            )
            resp.raise_for_status()
            prices.setdefault(symbol, {})["Binance"] = float(resp.json()["price"])
        except Exception:
            pass

    # Coinbase — symbol format: BTC-USD
    coinbase_map = {
        "BTC/USDT": "BTC-USD",
        "ETH/USDT": "ETH-USD",
        "SOL/USDT": "SOL-USD",
    }
    for symbol, cb_sym in coinbase_map.items():
        try:
            resp = requests.get(
                f"https://api.coinbase.com/v2/prices/{cb_sym}/spot",
                timeout=5,
            )
            resp.raise_for_status()
            prices.setdefault(symbol, {})["Coinbase"] = float(resp.json()["data"]["amount"])
        except Exception:
            pass

    # Kraken — symbol format: XBTUSDT
    kraken_map = {
        "BTC/USDT": "XBTUSDT",
        "ETH/USDT": "ETHUSDT",
        "SOL/USDT": "SOLUSDT",
    }
    for symbol, k_sym in kraken_map.items():
        try:
            resp = requests.get(
                "https://api.kraken.com/0/public/Ticker",
                params={"pair": k_sym},
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("error"):
                result = list(data["result"].values())[0]
                prices.setdefault(symbol, {})["Kraken"] = float(result["c"][0])
        except Exception:
            pass

    return prices


# ── Arbitrage detection ────────────────────────────────────────────────────────

def detect_and_store_alerts(prices: dict):
    """
    Scan the latest prices for arbitrage opportunities and append to _alerts.
    Deduplicates — the same symbol+exchange pair is only stored once per 30 s.
    """
    global _last_alert_key

    for symbol, exdata in prices.items():
        if len(exdata) < 2:
            continue

        min_ex = min(exdata, key=lambda e: exdata[e])
        max_ex = max(exdata, key=lambda e: exdata[e])
        buy_price  = exdata[min_ex]
        sell_price = exdata[max_ex]
        profit_pct = ((sell_price - buy_price) / buy_price) * 100

        if profit_pct < ARBITRAGE_THRESHOLD_PCT:
            continue

        dedup_key = f"{symbol}:{min_ex}:{max_ex}"
        now = time.time()
        if _alerts and _alerts[0].get("_key") == dedup_key:
            if (now - _alerts[0]["timestamp"]) < 30:
                continue  # same opportunity, too soon

        _alerts.appendleft({
            "symbol":       symbol,
            "buy_exchange": min_ex,
            "sell_exchange": max_ex,
            "buy_price":    buy_price,
            "sell_price":   sell_price,
            "profit_pct":   profit_pct,
            "timestamp":    now,
            "_key":         dedup_key,
        })


def get_alerts() -> list:
    return list(_alerts)
