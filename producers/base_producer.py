import logging
from kafka import KafkaProducer
from config import KAFKA_BROKER, TOPICS
from models.price_event import PriceEvent

logger = logging.getLogger(__name__)


class BaseProducer:
    """
    Abstract base class for exchange price producers.
    Subclasses implement fetch_prices() to pull data from a specific exchange.
    """

    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            # Partition by symbol so all prices for BTC go to the same partition
            value_serializer=lambda v: v.encode("utf-8"),
        )

    def fetch_prices(self) -> list:
        """Fetch latest prices from the exchange. Must return a list of PriceEvent."""
        raise NotImplementedError

    def publish(self, event: PriceEvent):
        """Send a single PriceEvent to the raw-prices Kafka topic."""
        self.producer.send(
            TOPICS["raw_prices"],
            key=event.symbol.encode("utf-8"),  # partition by symbol
            value=event.to_json(),
        )
        logger.info(f"[{self.exchange_name}] {event.symbol} @ ${event.price:>12,.2f}")

    def run_once(self):
        """Fetch prices and publish all of them. Called on a poll interval."""
        try:
            events = self.fetch_prices()
            for event in events:
                self.publish(event)
            self.producer.flush()
        except Exception as e:
            logger.error(f"[{self.exchange_name}] Failed to fetch/publish prices: {e}")

    def close(self):
        self.producer.close()
