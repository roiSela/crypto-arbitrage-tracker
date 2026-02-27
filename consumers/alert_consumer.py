import json
import logging

from kafka import KafkaConsumer
from config import KAFKA_BROKER, TOPICS

logger = logging.getLogger(__name__)

SEPARATOR = "=" * 58


class AlertConsumer:
    """
    Reads ArbitrageAlert messages from the arbitrage-alerts topic
    and prints them to the console.

    This is where you'd plug in real notifications:
    email, Slack webhook, Telegram bot, etc.

    Kafka concepts demonstrated:
      - Separate consumer group from the processor
      - Multiple independent consumers on different topics
      - Deserializing structured messages
    """

    def __init__(self):
        self.consumer = KafkaConsumer(
            TOPICS["alerts"],
            bootstrap_servers=KAFKA_BROKER,
            group_id="alert-notifier",
            value_deserializer=lambda v: v.decode("utf-8"),
            auto_offset_reset="latest",
        )

    def run(self):
        logger.info("[AlertConsumer] Started. Waiting for arbitrage opportunities...")
        for message in self.consumer:
            try:
                alert = json.loads(message.value)
                self._notify(alert)
            except Exception as e:
                logger.error(f"[AlertConsumer] Error: {e}")

    def _notify(self, alert: dict):
        symbol = alert["symbol"]
        buy_ex = alert["buy_exchange"]
        sell_ex = alert["sell_exchange"]
        buy_price = alert["buy_price"]
        sell_price = alert["sell_price"]
        profit_pct = alert["profit_pct"]

        print(f"\n{SEPARATOR}")
        print(f"  *** ARBITRAGE OPPORTUNITY DETECTED ***")
        print(SEPARATOR)
        print(f"  Symbol   : {symbol}")
        print(f"  BUY  on  : {buy_ex:<10}  @ ${buy_price:>13,.4f}")
        print(f"  SELL on  : {sell_ex:<10}  @ ${sell_price:>13,.4f}")
        print(f"  Spread   : {profit_pct:.4f}%")
        print(f"  Profit   : ${sell_price - buy_price:>10,.4f} per unit")
        print(f"{SEPARATOR}\n")
