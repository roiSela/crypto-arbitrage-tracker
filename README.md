# Crypto Arbitrage Tracker

A real-time crypto price arbitrage detector built with **Apache Kafka** and **Streamlit**.

Tracks BTC, ETH, and SOL prices across **Binance**, **Coinbase**, and **Kraken** simultaneously.
When the same coin is cheaper on one exchange than another, it fires an alert — including an
estimated net profit after fees.

**[Live Demo](https://crypto-arbitrage-tracker-8eewipchv9xackd8w6zmoq.streamlit.app)**

---

## How it works

```
Binance API ──┐
Coinbase API ──┼──► Kafka (raw-prices) ──► Arbitrage Processor ──► Kafka (alerts) ──► Dashboard
Kraken API  ──┘
```

- **3 Producers** poll exchange REST APIs every 10 seconds and publish price events to Kafka
- **Arbitrage Processor** consumes all prices, maintains a 30-second rolling window per symbol, and publishes an alert whenever the spread between any two exchanges exceeds the threshold
- **Streamlit Dashboard** consumes alerts and displays live prices, spreads, and trade instructions

## Features

- Live price comparison table (color-coded cheapest/most expensive per exchange)
- Spread indicator per coin with trade signal (TRADE IT / CLOSE / Watching)
- Trade instruction cards: step-by-step BUY on X → SELL on Y
- Profit simulator: calculates net profit after fees for any investment amount
- Two modes: full Kafka pipeline (local) or direct API mode (cloud deployment)

## Tech Stack

| Layer | Technology |
|---|---|
| Message broker | Apache Kafka (KRaft, via Docker) |
| Producers | Python + `kafka-python` + Exchange REST APIs |
| Stream processing | Python (stateful consumer group) |
| Dashboard | Streamlit + Pandas |
| Cloud deployment | Streamlit Community Cloud |

## Run locally

**Requirements:** Docker, Python 3.10+

```bash
# 1. Start Kafka
docker-compose up -d

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the pipeline (producers + processor)
python main.py

# 4. Start the dashboard (new terminal)
streamlit run dashboard/app.py
```

Open http://localhost:8501

## Project structure

```
├── config.py                    # Shared settings (topics, symbols, thresholds)
├── models/price_event.py        # PriceEvent dataclass
├── producers/
│   ├── base_producer.py         # Abstract base producer
│   ├── binance_producer.py
│   ├── coinbase_producer.py
│   └── kraken_producer.py
├── processor/
│   └── arbitrage_processor.py   # Detects spreads, publishes alerts
├── consumers/
│   └── alert_consumer.py        # Console alert output
├── dashboard/
│   ├── app.py                   # Streamlit UI
│   ├── kafka_state.py           # Background Kafka consumers for dashboard
│   └── cloud_fetcher.py         # Direct API mode (no Kafka needed)
└── docker-compose.yml           # Single-node Kafka (KRaft)
```

## Configuration

Edit `config.py` to adjust:

```python
ARBITRAGE_THRESHOLD_PCT = 0.3   # Minimum spread % to trigger an alert
POLL_INTERVAL_SECONDS   = 10    # How often producers fetch prices
PRICE_WINDOW_SECONDS    = 30    # How long a price is considered fresh
```
