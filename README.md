# Sentiment Terminal

A stock price and news sentiment tracker for technology companies. The project combines market data, news sentiment, and technical indicators into a data pipeline backed by Supabase Postgres and presented through an interactive Streamlit dashboard.

## What It Does

- Collects stock prices with `yfinance`
- Fetches ticker-level news sentiment from Alpha Vantage
- Computes RSI, MACD, realized volatility, and short-term returns
- Produces a composite signal and confidence score
- Stores price, sentiment, indicator, and signal data in Postgres
- Presents the results in a multi-view dashboard

## Dashboard

- **Market Pulse**: Compare the latest price, sentiment, confidence, and keywords across tracked tickers
- **Compare Assets**: Overlay price, sentiment, or confidence for up to four tickers
- **Sentiment Heatmap**: Review sentiment intensity by ticker and date
- **Asset Deep Dive**: Inspect a selected ticker's market mood, catalysts, and price/sentiment history

## Architecture

```text
GitHub Actions -> allinone.py -> Alpha Vantage + yfinance -> Supabase Postgres
																  |
																  v
														Streamlit dashboard
```

The scheduled workflow runs during weekday market hours. It is designed for periodic monitoring rather than tick-by-tick trading or real-time execution.

## Stack

- Python
- Streamlit
- Pandas and NumPy
- Plotly
- yfinance
- Alpha Vantage News Sentiment API
- Supabase Postgres
- GitHub Actions

## Configuration

Credentials are supplied through environment variables and are not committed to the repository:

- `SUPABASE_URL`: Supabase Postgres connection string
- `ALPHA_VANTAGE_API_KEY`: Alpha Vantage API key
- `TICKERS`: Optional comma-separated ticker list for the data harvester
- `TICKER`: Optional ticker for `graph.py`; defaults to `NVDA`

For Streamlit Cloud, configure `SUPABASE_URL` in the app's secrets settings. For GitHub Actions, configure `SUPABASE_URL` and `ALPHA_VANTAGE_API_KEY` as repository or environment secrets.

## Run Locally

```bash
cd DB_Setup
pip install -r requirements.txt
export SUPABASE_URL="your-supabase-connection-string"
export ALPHA_VANTAGE_API_KEY="your-alpha-vantage-key"
streamlit run dashboard.py
```

To run a data sync manually:

```bash
TICKERS="NVDA,AAPL,AMD,MSFT" python allinone.py
```

## Project Files

- `DB_Setup/allinone.py`: Data collection, indicator calculation, scoring, and database persistence
- `DB_Setup/dashboard.py`: Streamlit dashboard
- `DB_Setup/graph.py`: Static price and sentiment chart
- `DB_Setup/sentiment_fetcher.py`: Legacy sentiment fetcher
- `.github/workflows/nvda-sync.yml`: Scheduled GitHub Actions data sync

## Notes

This is a personal portfolio project for exploring data pipelines and signal design. Sentiment and market data depend on third-party APIs, and the resulting scores are for demonstration and research only. This project is not financial advice or a trading system.
