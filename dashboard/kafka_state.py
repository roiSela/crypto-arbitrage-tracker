"""
Shared in-memory state for the Streamlit dashboard.

Two background threads consume from Kafka topics and write into
thread-safe dictionaries. The Streamlit app reads from these on
every auto-refresh cycle.

This module is a singleton — the background threads start once
per process (guarded by _started flag) and keep running for the
lifetime of the Streamlit server.
"""

import json
import os
import sys
import threading
from collections import deque

from kafka import KafkaConsumer

# Make sure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import KAFKA_BROKER, TOPICS
from models.price_event import PriceEvent

_lock = threading.Lock()

# {symbol: {exchange: PriceEvent}}
_latest_prices: dict = {}

# Capped at 50 most recent alerts (newest first)
_alerts: deque = deque(maxlen=50)

_started = False


# ---------- Public API ----------

def get_prices() -> dict:
    with _lock:
        return {sym: dict(exs) for sym, exs in _latest_prices.items()}


def get_alerts() -> list:
    with _lock:
        return list(_alerts)


# ---------- Background consumers ----------

def _consume_prices():
    consumer = KafkaConsumer(
        TOPICS["raw_prices"],
        bootstrap_servers=KAFKA_BROKER,
        group_id="dashboard-prices",
        value_deserializer=lambda v: v.decode("utf-8"),
        auto_offset_reset="latest",
    )
    for message in consumer:
        try:
            event = PriceEvent.from_json(message.value)
            with _lock:
                if event.symbol not in _latest_prices:
                    _latest_prices[event.symbol] = {}
                _latest_prices[event.symbol][event.exchange] = event
        except Exception:
            pass


def _consume_alerts():
    consumer = KafkaConsumer(
        TOPICS["alerts"],
        bootstrap_servers=KAFKA_BROKER,
        group_id="dashboard-alerts",
        value_deserializer=lambda v: v.decode("utf-8"),
        auto_offset_reset="earliest",  # show historical alerts on startup
    )
    for message in consumer:
        try:
            alert = json.loads(message.value)
            with _lock:
                _alerts.appendleft(alert)
        except Exception:
            pass


def start_background_consumers():
    """Call once when the Streamlit app starts."""
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_consume_prices, daemon=True, name="dash-prices").start()
    threading.Thread(target=_consume_alerts, daemon=True, name="dash-alerts").start()
