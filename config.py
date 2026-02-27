KAFKA_BROKER = "localhost:9092"

TOPICS = {
    "raw_prices": "raw-prices",
    "alerts": "arbitrage-alerts",
}

# Crypto pairs to track (in standard symbol format)
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# Alert when price difference between any two exchanges exceeds this %
ARBITRAGE_THRESHOLD_PCT = 0.3

# How often each producer polls its exchange (seconds)
POLL_INTERVAL_SECONDS = 10

# Prices older than this are considered stale and ignored
PRICE_WINDOW_SECONDS = 30
