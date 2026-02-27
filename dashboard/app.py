"""
Streamlit dashboard for the Crypto Arbitrage Tracker.

Run with:
    streamlit run dashboard/app.py

Modes:
  USE_KAFKA=true  (default) — reads live data from a local Kafka broker.
                              Requires: python main.py running in another terminal.
  USE_KAFKA=false           — fetches prices directly from exchange APIs.
                              No Kafka needed. Used for Streamlit Cloud deployment.
"""

import os
import sys
import time

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import SYMBOLS, ARBITRAGE_THRESHOLD_PCT

# ── Mode selection ─────────────────────────────────────────────────────────────
# Set USE_KAFKA=false in Streamlit Cloud secrets (or your shell env) to enable
# cloud mode — no Kafka broker required.
USE_KAFKA = os.environ.get("USE_KAFKA", "true").lower() == "true"

if USE_KAFKA:
    from dashboard.kafka_state import start_background_consumers, get_prices as _kget_prices, get_alerts as _kget_alerts
else:
    from dashboard.cloud_fetcher import fetch_prices as _cloud_fetch, detect_and_store_alerts, get_alerts as _cget_alerts


def get_data():
    """Returns (prices, alerts) regardless of mode.
    prices format: {symbol: {exchange: float}}
    """
    if USE_KAFKA:
        start_background_consumers()
        raw = _kget_prices()
        # Normalise PriceEvent objects → plain floats
        prices = {sym: {ex: ev.price for ex, ev in exmap.items()} for sym, exmap in raw.items()}
        alerts = _kget_alerts()
    else:
        prices = _cloud_fetch()
        detect_and_store_alerts(prices)
        alerts = _cget_alerts()
    return prices, alerts

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Crypto Arbitrage Tracker",
    page_icon="🪙",
    layout="wide",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }

    .metric-card {
        background: #0e1117;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
        margin-bottom: 8px;
    }
    .metric-symbol    { font-size: 0.85rem; color: #888; margin-bottom: 4px; }
    .metric-price     { font-size: 1.6rem; font-weight: 700; color: #fff; }
    .metric-label     { font-size: 0.72rem; color: #555; margin-top: 6px; }
    .spread-ok        { font-size: 0.8rem; color: #00cc66; }
    .spread-hot       { font-size: 0.8rem; color: #ff9900; font-weight: 600; }
    .spread-tradeable { font-size: 0.8rem; color: #ff4444; font-weight: 700; }

    .trade-card {
        border-left: 4px solid;
        border-radius: 6px;
        padding: 14px 16px;
        margin-bottom: 12px;
        font-family: monospace;
        font-size: 0.82rem;
    }
    .trade-profitable   { background: #071a0e; border-color: #00cc66; }
    .trade-unprofitable { background: #1a0f07; border-color: #ff9900; }
    .trade-hot          { background: #1a0808; border-color: #ff4444; }

    .step-label {
        display: inline-block;
        background: #1e1e1e;
        border-radius: 4px;
        padding: 1px 7px;
        font-size: 0.7rem;
        color: #aaa;
        margin-right: 6px;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .profit-line { margin-top: 10px; padding-top: 10px; border-top: 1px solid #2a2a2a; }
</style>
""", unsafe_allow_html=True)

# ── Auto-refresh every 5 seconds ──────────────────────────────────────────────
st_autorefresh(interval=5000, key="autorefresh")

# ── Fetch live data (works in both Kafka and Cloud mode) ───────────────────────
prices, alerts = get_data()   # prices: {symbol: {exchange: float}}


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 What is this?")
    st.markdown("""
**Crypto arbitrage** means buying a coin on one exchange where it's cheap,
and simultaneously selling it on another exchange where it's more expensive —
pocketing the difference as profit.

This tracker watches **Binance**, **Coinbase**, and **Kraken** in real time and
alerts you the moment a price gap (spread) is large enough to be profitable
after fees.
""")

    st.markdown("---")
    st.markdown("## 💰 Profit Simulator")
    st.caption("Estimate your return on a real opportunity.")

    investment = st.slider(
        "Your investment ($)",
        min_value=100,
        max_value=10_000,
        value=1_000,
        step=100,
    )
    fee_pct = st.slider(
        "Fee per trade (%)",
        min_value=0.05,
        max_value=1.0,
        value=0.1,
        step=0.05,
        help="Typical fees: Binance 0.1%, Kraken 0.16-0.26%, Coinbase 0.5-1.0%"
    )
    total_fees_pct = fee_pct * 2  # one fee to buy, one fee to sell
    st.caption(f"Total round-trip fees: **{total_fees_pct:.2f}%** (buy + sell)")

    st.markdown("---")
    st.markdown("## 📋 How to trade an opportunity")
    st.markdown("""
1. **Open accounts** on both exchanges shown in the alert
2. **Have funds ready** on the BUY exchange (USDT or USD)
3. **BUY** the coin on the cheaper exchange immediately
4. **SELL** the coin on the more expensive exchange immediately
5. **Profit** = sell proceeds − buy cost − fees

> ⚠️ Speed matters — spreads close in seconds.
> Always check that the **Net Profit** is positive before trading.
""")

    st.markdown("---")
    st.markdown("## ⚙️ Alert threshold")
    st.caption(
        f"Alerts fire when the spread ≥ **{ARBITRAGE_THRESHOLD_PCT}%**. "
        f"Edit `ARBITRAGE_THRESHOLD_PCT` in `config.py` to change this."
    )


# ── HEADER ────────────────────────────────────────────────────────────────────
col_title, col_status = st.columns([6, 1])
with col_title:
    st.markdown("## 🪙 Crypto Arbitrage Tracker")
with col_status:
    st.markdown(
        "<div style='text-align:right;padding-top:18px;'>"
        "<span style='color:#00cc66;font-size:0.85rem;'>● LIVE</span></div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── METRIC CARDS ──────────────────────────────────────────────────────────────
st.markdown("#### Current Spreads — Is there an opportunity right now?")
st.caption(
    "A **spread** is the % price difference between the cheapest and most expensive exchange. "
    f"The higher the spread, the bigger the potential profit. "
    f"Alerts fire at ≥ {ARBITRAGE_THRESHOLD_PCT}%."
)

cols = st.columns(len(SYMBOLS))

for col, symbol in zip(cols, SYMBOLS):
    with col:
        exdata = prices.get(symbol, {})
        if exdata:
            vals   = list(exdata.values())
            avg    = sum(vals) / len(vals)
            spread = ((max(vals) - min(vals)) / min(vals)) * 100
            net    = spread - (fee_pct * 2)

            if net > 0:
                status_cls  = "spread-tradeable"
                status_text = f"🔴 TRADE IT — net +{net:.3f}% after fees"
            elif spread >= ARBITRAGE_THRESHOLD_PCT:
                status_cls  = "spread-hot"
                status_text = f"🟡 CLOSE — fees eat profit ({net:+.3f}%)"
            else:
                status_cls  = "spread-ok"
                status_text = f"✅ Watching — spread too small"

            min_ex = min(exdata, key=lambda e: exdata[e].price)
            max_ex = max(exdata, key=lambda e: exdata[e].price)

            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-symbol'>{symbol}</div>
                <div class='metric-price'>${avg:,.2f}</div>
                <div class='{status_cls}'>{status_text}</div>
                <div class='metric-label'>spread {spread:.4f}% &nbsp;|&nbsp;
                    cheap: {min_ex} &nbsp;→&nbsp; exp: {max_ex}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-symbol'>{symbol}</div>
                <div class='metric-price' style='color:#555;'>waiting…</div>
                <div class='metric-label'>no data yet</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── PRICE TABLE + ALERTS ──────────────────────────────────────────────────────
left, right = st.columns([2, 3])

# ── LEFT: price comparison table ──────────────────────────────────────────────
with left:
    st.markdown("#### 📊 Price Comparison Table")
    st.caption(
        "Each row is an exchange. Each column is a coin. "
        "**Green** = cheapest source to buy. **Red** = most expensive (best place to sell)."
    )
    if prices:
        exchanges = sorted({ex for sym_data in prices.values() for ex in sym_data})

        # Build raw float table for coloring, and formatted table for display
        raw = {}
        fmt = {}
        for exchange in exchanges:
            raw[exchange] = {}
            fmt[exchange] = {}
            for symbol in SYMBOLS:
                price = prices.get(symbol, {}).get(exchange)
                raw[exchange][symbol] = price if price is not None else None
                fmt[exchange][symbol] = f"${price:,.4f}" if price is not None else "—"

        df_raw = pd.DataFrame(raw).T
        df_fmt = pd.DataFrame(fmt).T
        df_fmt.index.name = "Exchange"

        # Apply green/red styling per column (symbol)
        def color_col(col):
            styles = [""] * len(col)
            valid = col.dropna()
            if len(valid) < 2:
                return styles
            mn, mx = valid.min(), valid.max()
            for i, val in enumerate(col):
                if val == mn:
                    styles[i] = "background-color:#0a2a12; color:#00cc66; font-weight:700"
                elif val == mx:
                    styles[i] = "background-color:#2a0a0a; color:#ff4444; font-weight:700"
            return styles

        styled = df_raw.style.apply(color_col, axis=0).format("${:,.4f}", na_rep="—")
        st.dataframe(styled, use_container_width=True, height=155)
        st.caption("🟢 Cheapest = buy here &nbsp;&nbsp; 🔴 Most expensive = sell here")
    else:
        st.info("Waiting for price data from Kafka…")

# ── RIGHT: trade instructions ──────────────────────────────────────────────────
with right:
    st.markdown("#### 🚨 Trade Opportunities")
    st.caption(
        "Each card is a detected opportunity. "
        "**Net profit** already deducts exchange fees. Only act when net profit is positive."
    )

    if alerts:
        for alert in alerts[:8]:
            gross_pct  = alert["profit_pct"]
            net_pct    = gross_pct - (fee_pct * 2)
            gross_usd  = investment * (gross_pct / 100)
            fees_usd   = investment * (total_fees_pct / 100)
            net_usd    = gross_usd - fees_usd
            ts         = time.strftime("%H:%M:%S", time.localtime(alert["timestamp"]))

            if net_pct > 0:
                card_cls     = "trade-profitable"
                verdict      = f"✅ PROFITABLE after fees"
                verdict_col  = "#00cc66"
            else:
                card_cls     = "trade-unprofitable"
                verdict      = f"⚠️ NOT profitable — fees ({total_fees_pct:.2f}%) exceed spread"
                verdict_col  = "#ff9900"

            st.markdown(f"""
            <div class='trade-card {card_cls}'>
                <b style='font-size:0.95rem;'>⚡ {alert["symbol"]}</b>
                <span style='float:right; color:#666; font-size:0.75rem;'>{ts}</span>

                <div style='margin-top:10px; line-height:2;'>
                    <span class='step-label'>STEP 1 · BUY</span>
                    <b>{alert["buy_exchange"]}</b>
                    &nbsp;@&nbsp; <b>${alert["buy_price"]:,.4f}</b>
                    <span style='color:#555;'> ← cheaper exchange</span>
                    <br>
                    <span class='step-label'>STEP 2 · SELL</span>
                    <b>{alert["sell_exchange"]}</b>
                    &nbsp;@&nbsp; <b>${alert["sell_price"]:,.4f}</b>
                    <span style='color:#555;'> ← pricier exchange</span>
                </div>

                <div class='profit-line'>
                    <table style='width:100%; font-size:0.8rem; border-collapse:collapse;'>
                        <tr>
                            <td style='color:#aaa;'>Gross spread</td>
                            <td style='color:#fff; text-align:right;'>
                                +{gross_pct:.4f}%
                                &nbsp;<span style='color:#555;'>(+${gross_usd:,.2f} on ${investment:,})</span>
                            </td>
                        </tr>
                        <tr>
                            <td style='color:#aaa;'>Est. fees ({fee_pct:.2f}% × 2)</td>
                            <td style='color:#ff6666; text-align:right;'>
                                −{total_fees_pct:.2f}%
                                &nbsp;<span style='color:#555;'>(−${fees_usd:,.2f})</span>
                            </td>
                        </tr>
                        <tr style='border-top:1px solid #333;'>
                            <td style='color:#aaa; padding-top:4px;'><b>Net profit</b></td>
                            <td style='color:{verdict_col}; text-align:right; padding-top:4px;'>
                                <b>{net_pct:+.4f}%
                                &nbsp;(${net_usd:+,.2f} on ${investment:,})</b>
                            </td>
                        </tr>
                    </table>
                    <div style='margin-top:8px; color:{verdict_col}; font-weight:600;'>
                        {verdict}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"No opportunities detected yet (threshold: {ARBITRAGE_THRESHOLD_PCT}%). "
                f"Lower it in config.py to see more alerts.")

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"Tracking: {' · '.join(SYMBOLS)} &nbsp;|&nbsp; "
    f"Sources: Binance · Coinbase · Kraken &nbsp;|&nbsp; "
    f"Refreshes every 5s &nbsp;|&nbsp; "
    f"Last updated: {time.strftime('%H:%M:%S')} &nbsp;|&nbsp; "
    f"⚠️ For educational purposes — not financial advice"
)
