import requests
from producers.base_producer import BaseProducer
from models.price_event import PriceEvent

EXCHANGE_NAME = "Coinbase"
API_URL = "https://api.coinbase.com/v2/prices/{}/spot"

# Coinbase uses "BTC-USD" format
SYMBOL_MAP = {
    "BTC/USDT": "BTC-USD",
    "ETH/USDT": "ETH-USD",
    "SOL/USDT": "SOL-USD",
}


class CoinbaseProducer(BaseProducer):
    def __init__(self):
        super().__init__(EXCHANGE_NAME)

    def fetch_prices(self) -> list:
        events = []
        for symbol, cb_symbol in SYMBOL_MAP.items():
            resp = requests.get(API_URL.format(cb_symbol), timeout=5)
            resp.raise_for_status()
            price = float(resp.json()["data"]["amount"])
            events.append(PriceEvent(exchange=EXCHANGE_NAME, symbol=symbol, price=price))
        return events
