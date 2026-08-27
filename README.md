# Stock Tracker - DB Setup Folder

This folder contains the core scripts for your stock price and sentiment tracking system. It follows a simple workflow: fetch data, store it, and visualize trends.

## Configuration
Edit `config.json` to change the stock ticker, API keys, and database URL:
- `ticker`: The stock symbol (e.g., "NVDA", "AAPL")
- `alpha_vantage_api_key`: Your Alpha Vantage API key for sentiment data
- `supabase_url`: Your Supabase database connection string

## Workflow Overview
1. **Foundation**: Supabase PostgreSQL database stores unified price and sentiment data.
2. **Data Input**: `allinone.py` - Fetches real-time stock data and sentiment.
3. **Visualization**: `graph.py` - Generates charts showing price vs. sentiment over time.

## Files
- `allinone.py`: Main data harvester. Run this to fetch and save data.
- `graph.py`: Visualization script. Run this to create price-sentiment charts.
- `config.json`: Configuration file for ticker and credentials.
- `sentiment_fetcher.py`: Legacy sentiment fetcher (integrated into allinone.py).

## Getting Started
1. Update `config.json` with your desired ticker.
2. Run `python allinone.py` to harvest data.
3. Run `python graph.py` to visualize.

## GitHub Actions
The automated workflow reads from `config.json`, so changes here apply to cloud runs too.