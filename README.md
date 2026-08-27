# Stock Tracker - DB Setup Folder

This folder contains the core scripts for your stock price and sentiment tracking system. It follows a simple workflow: fetch data, store it, and visualize trends.

## Configuration

Credentials are supplied through environment variables and are not stored in this repository:

- `SUPABASE_URL`: Your Supabase database connection string
- `ALPHA_VANTAGE_API_KEY`: Your Alpha Vantage API key for sentiment data
- `TICKER`: Optional stock symbol for `graph.py` (defaults to `NVDA`)

## Workflow Overview

1. **Foundation**: Supabase PostgreSQL database stores unified price and sentiment data.
2. **Data Input**: `allinone.py` - Fetches real-time stock data and sentiment.
3. **Visualization**: `graph.py` - Generates charts showing price vs. sentiment over time.

## Files

- `allinone.py`: Main data harvester. Run this to fetch and save data.
- `graph.py`: Visualization script. Run this to create price-sentiment charts.
- `sentiment_fetcher.py`: Legacy sentiment fetcher (integrated into allinone.py).

## Getting Started

1. Set `SUPABASE_URL` and `ALPHA_VANTAGE_API_KEY` in your local environment.
2. Run `python allinone.py` to harvest data.
3. Run `TICKER=NVDA python graph.py` to visualize.

## GitHub Actions

The automated workflow reads `SUPABASE_URL` and `ALPHA_VANTAGE_API_KEY` from GitHub Actions Secrets. The Streamlit deployment reads `SUPABASE_URL` from its configured Streamlit secret.
