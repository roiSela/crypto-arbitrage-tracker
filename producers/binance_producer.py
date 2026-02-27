import requests
from producers.base_producer import BaseProducer
from models.price_event import PriceEvent
from config import SYMBOLS

EXCHANGE_NAME = "Binance"
API_URL = "https://api.binance.com/api/v3/ticker/price"

# Binance uses "BTCUSDT" format (no slash)
SYMBOL_MAP = {s: s.replace("/", "") for s in SYMBOLS}


class BinanceProducer(BaseProducer):
    def __init__(self):
        super().__init__(EXCHANGE_NAME)

    def fetch_prices(self) -> list:
        events = []
        for symbol, binance_symbol in SYMBOL_MAP.items():
            resp = requests.get(API_URL, params={"symbol": binance_symbol}, timeout=5)
            resp.raise_for_status()
            price = float(resp.json()["price"])
            events.append(PriceEvent(exchange=EXCHANGE_NAME, symbol=symbol, price=price))
        return events
