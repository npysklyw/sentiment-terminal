import yfinance as yf
import psycopg2
from datetime import datetime
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Supabase PostgreSQL connection string
SUPABASE_URL = os.environ['SUPABASE_URL']

def fetch_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        return {
            'price': info['last_price'],
            'volume': info['last_volume']
        }
    except Exception as e:
        logging.error(f"Failed to fetch data for {ticker}: {e}")
        return None

def save_to_database(timestamp, ticker, price, sentiment_score, source, volume):
    try:
        with psycopg2.connect(SUPABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS combined_data (
                        timestamp TIMESTAMP,
                        ticker TEXT,
                        price REAL,
                        sentiment_score REAL,
                        source TEXT,
                        volume BIGINT
                    )
                ''')
                cursor.execute('''
                    INSERT INTO combined_data (timestamp, ticker, price, sentiment_score, source, volume)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (timestamp, ticker, price, sentiment_score, source, volume))
                conn.commit()
                logging.info(f"Synced: {timestamp} | Ticker: {ticker} | Price: ${price:.2f} | Sentiment: {sentiment_score}")
    except Exception as e:
        logging.error(f"Failed to save data to database: {e}")

def sync_market_data(sentiment_score, source="Manual", ticker="NVDA"):
    data = fetch_stock_data(ticker)
    if data is None:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_to_database(timestamp, ticker, data['price'], sentiment_score, source, data['volume'])

if __name__ == "__main__":
    sync_market_data(0.0, source="Automated")