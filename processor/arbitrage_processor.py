import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, asdict

from kafka import KafkaConsumer, KafkaProducer
from config import KAFKA_BROKER, TOPICS, ARBITRAGE_THRESHOLD_PCT, PRICE_WINDOW_SECONDS
from models.price_event import PriceEvent

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageAlert:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    profit_pct: float
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class ArbitrageProcessor:
    """
    Kafka Streams-style processor (implemented manually in Python).

    Reads from the raw-prices topic.
    Maintains a rolling window of the latest price per (symbol, exchange).
    When prices from 2+ exchanges are available for the same symbol,
    checks if the spread exceeds ARBITRAGE_THRESHOLD_PCT and publishes an alert.

    Kafka concepts demonstrated:
      - Consumer groups (this processor has its own group ID)
      - Stateful stream processing (in-memory price window)
      - Fan-in: aggregating messages across multiple producers
      - Producer inside a consumer (read → process → write)
    """

    def __init__(self):
        self.consumer = KafkaConsumer(
            TOPICS["raw_prices"],
            bootstrap_servers=KAFKA_BROKER,
            group_id="arbitrage-processor",
            value_deserializer=lambda v: v.decode("utf-8"),
            auto_offset_reset="latest",
        )
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: v.encode("utf-8"),
        )
        # latest_prices[symbol][exchange] = PriceEvent
        self.latest_prices: dict = defaultdict(dict)

    def _prune_stale(self, symbol: str):
        """Remove prices older than PRICE_WINDOW_SECONDS."""
        now = time.time()
        self.latest_prices[symbol] = {
            ex: ev
            for ex, ev in self.latest_prices[symbol].items()
            if (now - ev.timestamp) <= PRICE_WINDOW_SECONDS
        }

    def _check_arbitrage(self, symbol: str):
        self._prune_stale(symbol)
        prices = self.latest_prices[symbol]

        if len(prices) < 2:
            return  # Need at least 2 exchanges to compare

        min_ex = min(prices, key=lambda ex: prices[ex].price)
        max_ex = max(prices, key=lambda ex: prices[ex].price)

        buy_price = prices[min_ex].price
        sell_price = prices[max_ex].price
        profit_pct = ((sell_price - buy_price) / buy_price) * 100

        if profit_pct >= ARBITRAGE_THRESHOLD_PCT:
            alert = ArbitrageAlert(
                symbol=symbol,
                buy_exchange=min_ex,
                sell_exchange=max_ex,
                buy_price=buy_price,
                sell_price=sell_price,
                profit_pct=profit_pct,
            )
            self.producer.send(
                TOPICS["alerts"],
                key=symbol.encode("utf-8"),
                value=alert.to_json(),
            )
            self.producer.flush()
            logger.info(
                f"[Processor] Alert published — {symbol}: "
                f"Buy {min_ex} @ ${buy_price:,.2f}, "
                f"Sell {max_ex} @ ${sell_price:,.2f} "
                f"({profit_pct:.3f}%)"
            )

    def run(self):
        logger.info("[Processor] Started. Listening on raw-prices topic...")
        for message in self.consumer:
            try:
                event = PriceEvent.from_json(message.value)
                self.latest_prices[event.symbol][event.exchange] = event
                self._check_arbitrage(event.symbol)
            except Exception as e:
                logger.error(f"[Processor] Error handling message: {e}")
