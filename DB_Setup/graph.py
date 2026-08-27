import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import datetime
import os
from datetime import datetime  # <--- FIX 1: Import the class specifically

# ... other imports ...

# FIX 2: To avoid the SQLAlchemy warning, use the connection directly 
# but pass it as a context manager or just ignore the warning for now.
# To ignore the warning, you can add this at the very top:
# import warnings
# warnings.filterwarnings("ignore", category=UserWarning)


# 1. Load deployment configuration from environment variables
SUPABASE_URL = os.environ['SUPABASE_URL']
TICKER = os.environ.get('TICKER', 'NVDA')

# 2. Connect to Supabase
conn = psycopg2.connect(SUPABASE_URL)
# Pulling last 50 points to see the trend
query = f"SELECT * FROM combined_data WHERE ticker='{TICKER}' ORDER BY timestamp DESC LIMIT 50"
df = pd.read_sql_query(query, conn)
conn.close()

if df.empty:
    print(f"No data available in Supabase for {TICKER}.")
    exit()

# Important: Sort by time ASCENDING for the graph
df = df.sort_values('timestamp')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 3. Setup the Dual-Axis Chart
fig, ax1 = plt.subplots(figsize=(14, 7))

# --- Plot the Price (Line Chart) ---
color_price = '#007acc' # Modern blue
ax1.set_xlabel('Date/Time', fontsize=10)
ax1.set_ylabel(f'{TICKER} Price ($)', color=color_price, fontsize=12, fontweight='bold')
ax1.plot(df['timestamp'], df['price'], color=color_price, marker='o', markersize=4, linewidth=2.5, label='Price')
ax1.tick_params(axis='y', labelcolor=color_price)
ax1.grid(True, linestyle='--', alpha=0.5)

# Format price axis
ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter('$%.2f'))
padding = (df['price'].max() - df['price'].min()) * 0.1
ax1.set_ylim(df['price'].min() - padding, df['price'].max() + padding)

# --- Plot the Sentiment (Bar Chart) ---
ax2 = ax1.twinx()
ax2.set_ylabel('Sentiment Score (-1 to 1)', color='#333333', fontsize=12, fontweight='bold')
colors = ['#2ca02c' if s > 0 else '#d62728' for s in df['sentiment_score']]

# Calculate dynamic width (approx 70% of the time difference between points)
ax2.bar(df['timestamp'], df['sentiment_score'], color=colors, alpha=0.35, width=0.03, label='Sentiment')
ax2.set_ylim(-1.1, 1.1)
ax2.axhline(0, color='black', linewidth=0.8, alpha=0.3) # Zero line for sentiment

# 4. Format the X-Axis Dates (Stop the overlap!)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
plt.xticks(rotation=45)

# 5. Title and Metadata
plt.title(f'{TICKER} Market Pulse: Price vs. Weighted Sentiment\nGenerated on {datetime.now().strftime("%Y-%m-%d")}', fontsize=15, fontweight='bold', pad=20)
fig.tight_layout()

# 6. Save to root directory (Ensures GitHub Action finds it)
file_name = f"{TICKER.lower()}_market_pulse.png"
plt.savefig(file_name, dpi=300)
print(f"Chart generated successfully: {file_name}")