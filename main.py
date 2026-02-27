"""
Crypto Arbitrage Tracker — main entry point.

Architecture:
  Producers  (Binance, Coinbase, Kraken)
      |
      v  [Kafka topic: raw-prices]
      |
  ArbitrageProcessor  (detects price spreads)
      |
      v  [Kafka topic: arbitrage-alerts]
      |
  AlertConsumer  (prints opportunities to console)

Each producer and the processor run in daemon threads.
The alert consumer blocks on the main thread.
"""

import logging
import threading
import time

from config import POLL_INTERVAL_SECONDS
from producers.binance_producer import BinanceProducer
from producers.coinbase_producer import CoinbaseProducer
from producers.kraken_producer import KrakenProducer
from processor.arbitrage_processor import ArbitrageProcessor
from consumers.alert_consumer import AlertConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_producer_loop(producer):
    """Poll an exchange every POLL_INTERVAL_SECONDS and publish to Kafka."""
    logger.info(f"[{producer.exchange_name}] Producer thread started.")
    while True:
        producer.run_once()
        time.sleep(POLL_INTERVAL_SECONDS)


def main():
    logger.info("=" * 58)
    logger.info("  Crypto Arbitrage Tracker  |  Kafka Edition")
    logger.info("=" * 58)
    logger.info(f"  Tracking : BTC/USDT  ETH/USDT  SOL/USDT")
    logger.info(f"  Sources  : Binance | Coinbase | Kraken")
    logger.info(f"  Threshold: {0.3}% spread to trigger alert")
    logger.info("=" * 58)

    producers = [
        BinanceProducer(),
        CoinbaseProducer(),
        KrakenProducer(),
    ]
    processor = ArbitrageProcessor()
    alert_consumer = AlertConsumer()

    # One daemon thread per producer
    for p in producers:
        t = threading.Thread(
            target=run_producer_loop,
            args=(p,),
            daemon=True,
            name=f"producer-{p.exchange_name}",
        )
        t.start()

    # Processor in its own daemon thread
    t = threading.Thread(target=processor.run, daemon=True, name="processor")
    t.start()

    # Alert consumer blocks the main thread (keeps the process alive)
    alert_consumer.run()


if __name__ == "__main__":
    main()
