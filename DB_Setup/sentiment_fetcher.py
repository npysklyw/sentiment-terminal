import requests
import sqlite3
import json
import os

API_KEY = os.environ['ALPHA_VANTAGE_API_KEY']

symbol = 'NVDA'
#url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={API_KEY}'
# Added &limit=100 to the end of the URL
#url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&limit=20&apikey={API_KEY}'

# r = requests.get(url)
# data = r.json()

# print(data)
FILENAME = 'stock_data_cache.json'

# # Grab the first news story
# stories = data['feed'][0:100]
# Logic: If we already have the data, just load it from the disk
if os.path.exists(FILENAME):
    print("Loading data from local cache...")
    with open(FILENAME, 'r') as f:
        data = json.load(f)
else:
    print("No cache found. Calling API...")
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={API_KEY}'
    r = requests.get(url)
    data = r.json()
    
    # Check for the error you just saw
    if 'feed' not in data:
        print("ERROR: API did not return news. Check your limits!")
        print(f"Server says: {data}")
        exit()
    
    # Save it so we don't have to call the API again
    with open(FILENAME, 'w') as f:
        json.dump(data, f, indent=4)
    print("Data saved to file!")

# Now 'data' is always available here, whether from API or File
stories = data['feed']
# # print(ten_story)
# # print(f"Headline: {first_story['title']}")
# #print(f"Sentiment: {ten_story[0]['overall_sentiment_label']}")

averages = []
# Set a threshold: only care if Intel is a main topic (> 50% relevance)
relevance_threshold = 0.5 

for x in stories:
    # Find the specific sentiment data for Intel within this article
    ticker_data = [t for t in x['ticker_sentiment'] if t['ticker'] == 'NVDA']
    
    if ticker_data:
        relevance = float(ticker_data[0]['relevance_score'])
        sentiment = float(ticker_data[0]['ticker_sentiment_score'])
        
        # Only append if the AI thinks the article is actually ABOUT Intel
        if relevance > relevance_threshold:
            # OPTIONAL: Weight the score by relevance
            # A 0.9 relevance score 'counts' more than a 0.5
            averages.append(sentiment * relevance)

if averages:
    print(f"Volume-Weighted Sentiment for {symbol}: {sum(averages) / len(averages):.4f}")
else:
    print("No highly relevant news found in this batch.")


# ... after your loop where you calculate sentiment ...

conn = sqlite3.connect('markets.db')
cursor = conn.cursor()

for x in stories:
    ticker_data = [t for t in x['ticker_sentiment'] if t['ticker'] == symbol]
    if ticker_data:
        rel = float(ticker_data[0]['relevance_score'])
        sent = float(ticker_data[0]['ticker_sentiment_score'])
        
        if rel > 0.5:
            # Insert the story into our database
            cursor.execute('''
                INSERT INTO sentiment_logs (ticker, headline, sentiment_score, relevance_score, source)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, x['title'], sent, rel, x['source']))

conn.commit()
conn.close()
print(f"Success! {symbol} data saved to markets.db")