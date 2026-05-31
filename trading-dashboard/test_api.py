import urllib.request
import json
import time

# Give the server a moment to start
time.sleep(2)

urls = [
    "http://localhost:5000/api/symbols",
    "http://localhost:5000/api/bars?symbol=AAPL&timeframe=1d&limit=10",
    "http://localhost:5000/api/bars?symbol=BTC/USD&timeframe=1h&limit=10"
]
for url in urls:
    print(f"\n--- URL: {url} ---")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            # just print first few items if it's a long list to keep output readable, though limit is 10 here
            if isinstance(data, list) and len(data) > 3 and "bars" not in url:
                print("[\n  " + ",\n  ".join([json.dumps(i) for i in data[:3]]) + ",\n  ...\n]")
            else:
                print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")
