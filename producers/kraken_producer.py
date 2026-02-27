import requests
from producers.base_producer import BaseProducer
from models.price_event import PriceEvent

EXCHANGE_NAME = "Kraken"
API_URL = "https://api.kraken.com/0/public/Ticker"

# Kraken uses "XBTUSDT" for BTC (their legacy naming)
SYMBOL_MAP = {
    "BTC/USDT": "XBTUSDT",
    "ETH/USDT": "ETHUSDT",
    "SOL/USDT": "SOLUSDT",
}


class KrakenProducer(BaseProducer):
    def __init__(self):
        super().__init__(EXCHANGE_NAME)

    def fetch_prices(self) -> list:
        events = []
        for symbol, kraken_symbol in SYMBOL_MAP.items():
            resp = requests.get(API_URL, params={"pair": kraken_symbol}, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                continue
            # Kraken returns a dict keyed by pair name (may differ from requested)
            result = list(data["result"].values())[0]
            price = float(result["c"][0])  # "c" = last trade closed [price, lot_volume]
            events.append(PriceEvent(exchange=EXCHANGE_NAME, symbol=symbol, price=price))
        return events
