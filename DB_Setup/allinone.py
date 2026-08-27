# FULLY INTEGRATED ENHANCED SENTIMENT PIPELINE (PRODUCTION READY)

import json
import yfinance as yf
from datetime import datetime
import logging
import requests
import os
import math
import time
import numpy as np

try:
    import psycopg2
except ImportError:
    psycopg2 = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.json')
try:
    with open(CONFIG_PATH, 'r') as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    config = {}

SUPABASE_URL = os.environ.get('SUPABASE_URL') or config.get('supabase_url')

ALPHA_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY') or config.get('alpha_vantage_api_key')
DEFAULT_TICKER = config.get('ticker', 'NVDA')


COMPANY_KEYWORDS = {
    "NVDA": ["AI", "GPU", "H100", "chip", "semiconductor"],
    "AMD": ["CPU", "GPU", "chip", "semiconductor"],
    "AAPL": ["iPhone", "Mac", "Apple Watch", "services", "retail"],
    "AMZN": ["AWS", "Prime", "retail", "cloud", "logistics"],
    "MSFT": ["Azure", "Windows", "Office", "cloud", "AI"],
    "GOOGL": ["Google", "Alphabet", "YouTube", "Gemini", "cloud", "AI"],
    "META": ["Facebook", "Instagram", "Reality Labs", "Llama", "AI", "advertising"],
    # ... add for all tickers you track
}


# --- CONFIG VALIDATION ---
if not SUPABASE_URL:
    raise ValueError("Missing SUPABASE_URL")
if not ALPHA_KEY:
    raise ValueError("Missing ALPHA_VANTAGE_API_KEY")

def extract_company_keywords(ticker, text, max_keywords=5):
    """
    Extract top keywords for a specific company from a text string.
    Returns a comma-separated string and count of matches.
    """
    text_lower = text.lower()
    keywords = COMPANY_KEYWORDS.get(ticker, [])
    found = []
    for kw in keywords:
        if kw.lower() in text_lower:
            found.append(kw)
        if len(found) >= max_keywords:
            break
    return ", ".join(found), len(found)
# --- HELPERS ---
def clean_numbers(arr):
    return [float(x) for x in arr if x is not None]


def safe_avg(arr):
    arr = clean_numbers(arr)
    return sum(arr) / len(arr) if arr else 0.0
def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        num = float(value)
        if math.isnan(num) or math.isinf(num):
            return default
        return num
    except:
        return default
def ema(values, period):
    if not values:
        return []
    multiplier = 2 / (period + 1)
    ema_values = [values[0]]
    for val in values[1:]:
        ema_values.append((val - ema_values[-1]) * multiplier + ema_values[-1])
    return ema_values

# --- RSI ---
def calculate_rsi(closes, period=14):
    if len(closes) <= period:
        return 50.0  # neutral RSI if not enough data

    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- MACD ---
def calculate_macd(closes):
    if len(closes) < 35:
        return 0.0, 0.0  # not enough data for EMA26 + signal

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal_line = ema(macd_line, 9)

    if not signal_line:
        return 0.0, 0.0
    return macd_line[-1], signal_line[-1]

# --- Volatility ---
def calculate_volatility(closes, window=20):
    if len(closes) <= window:
        return 0.0  # not enough data

    returns = []
    for i in range(len(closes) - window, len(closes)):
        prev = closes[i - 1]
        cur = closes[i]
        if prev:
            returns.append((cur / prev) - 1)

    if len(returns) < 2:
        return 0.0

    avg = sum(returns) / len(returns)
    variance = sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance)

# --- FEATURE ENGINEERING ---
def fetch_market_features(ticker):
    hist = yf.Ticker(ticker).history(period="3mo")

    if hist.empty or "Close" not in hist:
        return {
            "return_1d": 0,
            "return_5d": 0,
            "rsi_14": 50,
            "macd": 0,
            "macd_signal": 0,
            "volatility_20d": 0
        }

    closes = clean_numbers(hist["Close"].tolist())

    if len(closes) < 30:
        return {
            "return_1d": 0,
            "return_5d": 0,
            "rsi_14": 50,
            "macd": 0,
            "macd_signal": 0,
            "volatility_20d": 0
        }

    macd, macd_signal = calculate_macd(closes)

    return {
        "return_1d": (closes[-1] / closes[-2]) - 1 if len(closes) > 1 else 0,
        "return_5d": (closes[-1] / closes[-6]) - 1 if len(closes) > 6 else 0,
        "rsi_14": calculate_rsi(closes),
        "macd": macd,
        "macd_signal": macd_signal,
        "volatility_20d": calculate_volatility(closes)
    }


def fetch_avg_volume(ticker):
    hist = yf.Ticker(ticker).history(period="30d")
    if hist.empty or "Volume" not in hist:
        return 1.0

    vols = clean_numbers(hist["Volume"].tolist())
    return safe_avg(vols) or 1.0


def fetch_realtime_quote(ticker):
    stock = yf.Ticker(ticker)
    data = stock.history(period="1d", interval="1m")

    if data.empty:
        return 0.0, 0

    return safe_float(data["Close"].iloc[-1]), int(safe_float(data["Volume"].iloc[-1]))


# --- SENTIMENT ---
KEYWORDS = ["ai", "gpu", "chip", "datacenter", "model", "llm", "semiconductor"]

def fetch_sentiment(ticker):
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_KEY}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data.get("Note") or data.get("Information") or data.get("Error Message"):
        message = data.get("Note") or data.get("Information") or data.get("Error Message")
        raise RuntimeError(f"Alpha Vantage API error for {ticker}: {message}")

    feed = data.get("feed")
    if not isinstance(feed, list):
        raise RuntimeError(f"Alpha Vantage returned no news feed for {ticker}")

    scores = []
    found_keywords = []

    for item in feed:
        summary = (item.get("title","") + item.get("summary",""))

        # ticker sentiment
        for t in item.get("ticker_sentiment", []):
            if t["ticker"] == ticker:
                val = t.get("ticker_sentiment_score")
                if val is not None:
                    scores.append(float(val))

        # company-specific keyword extraction
        kws, _ = extract_company_keywords(ticker, summary)
        if kws:
            found_keywords.extend(kws.split(", "))

    if not scores:
        logging.warning("No ticker sentiment scores returned for %s", ticker)

    avg = sum(scores) / len(scores) if scores else 0.0
    unique_keywords = list(dict.fromkeys(found_keywords))[:5]  # top 5, remove duplicates
    return avg, ", ".join(unique_keywords), len(unique_keywords)


# --- SIGNAL ---
def calculate_signal(news_sent, features, volume, avg_volume):
    momentum = math.tanh(features["return_5d"] * 8)
    rsi = (features["rsi_14"] - 50) / 50
    macd = 1 if features["macd"] > features["macd_signal"] else -1

    signal = news_sent * 0.5 + momentum * 0.25 + rsi * 0.15 + macd * 0.1

    vol_ratio = volume / avg_volume if avg_volume else 1
    signal *= (0.8 + 0.2 * min(vol_ratio, 2))

    return max(min(signal, 1), -1)


def calculate_sentiment_delta(current, history):
    return current - safe_avg(history)


def calculate_confidence(news_sent, features, keyword_count, delta):
    news_strength = min(abs(news_sent) * 1.5, 1)
    keyword_strength = min(keyword_count / 3, 1)

    trend = features["return_5d"]
    alignment = 1 if (trend >= 0 and news_sent >= 0) or (trend < 0 and news_sent < 0) else 0.4

    vol_penalty = min(features["volatility_20d"] * 10, 0.3)
    delta_boost = min(abs(delta) * 2, 0.3)

    conf = (0.35 * news_strength + 0.25 * keyword_strength + 0.25 * alignment + delta_boost - vol_penalty)
    return max(min(conf, 1), 0.05)


# --- DB ---
def fetch_sentiment_history(ticker):
    if psycopg2 is None:
        return []

    try:
        with psycopg2.connect(SUPABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT sentiment_score FROM combined_data
                    WHERE ticker=%s ORDER BY timestamp DESC LIMIT 5
                """, (ticker,))
                return [r[0] for r in cur.fetchall()]
    except:
        return []


def save_to_db(ticker, price, signal, confidence,
               news_sent, keywords, keyword_count, volume, features):

    if psycopg2 is None:
        return

    try:
        with psycopg2.connect(SUPABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO combined_data (
                        timestamp, ticker, price, sentiment_score, retail_sentiment,
                        top_keywords, source, volume,
                        return_1d, return_5d, rsi_14,
                        macd, macd_signal, volatility_20d,
                        signal_strength, confidence, keyword_count
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    datetime.now(),
                    ticker,
                    float(price),
                    float(news_sent),
                    0.0,
                    keywords,
                    "v3_pipeline",
                    int(volume),
                    float(features["return_1d"]),
                    float(features["return_5d"]),
                    float(features["rsi_14"]),
                    float(features["macd"]),
                    float(features["macd_signal"]),
                    float(features["volatility_20d"]),
                    float(signal),
                    float(confidence),
                    int(keyword_count)
                ))
                conn.commit()

    except Exception as e:
        logging.error(f"DB Error: {e}")


# --- MAIN ---
if __name__ == "__main__":
    tickers = [ticker.strip() for ticker in
               os.environ.get("TICKERS", DEFAULT_TICKER).split(",") if ticker.strip()]

    for t in tickers:
        try:
            logging.info(f"Processing {t}")

            price, volume = fetch_realtime_quote(t)
            if price == 0:
                continue

            avg_volume = fetch_avg_volume(t)

            news_sent, keywords, keyword_count = fetch_sentiment(t)
            features = fetch_market_features(t)

            history = fetch_sentiment_history(t)
            delta = calculate_sentiment_delta(news_sent, history)

            if keyword_count == 0 and abs(news_sent) < 0.15:
                continue

            signal = calculate_signal(news_sent, features, volume, avg_volume)
            confidence = calculate_confidence(news_sent, features, keyword_count, delta)

            save_to_db(
                t, price, signal, confidence,
                news_sent, keywords, keyword_count,
                volume, features
            )

            logging.info(f"{t} | Signal={signal:.3f} Confidence={confidence:.3f}")

            time.sleep(15)

        except Exception as e:
            logging.error(f"Failure on {t}: {e}")