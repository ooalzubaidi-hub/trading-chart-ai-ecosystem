import urllib.request, json, sys

tests = [
    ("Supertrend", "http://127.0.0.1:5000/api/indicator?symbol=BTC/USD&timeframe=1d&indicator=supertrend"),
    ("Stochastic", "http://127.0.0.1:5000/api/indicator?symbol=BTC/USD&timeframe=1d&indicator=stoch"),
    ("RSI",        "http://127.0.0.1:5000/api/indicator?symbol=BTC/USD&timeframe=1d&indicator=rsi"),
    ("MACD",       "http://127.0.0.1:5000/api/indicator?symbol=BTC/USD&timeframe=1d&indicator=macd"),
    ("BBands",     "http://127.0.0.1:5000/api/indicator?symbol=BTC/USD&timeframe=1d&indicator=bbands"),
    ("Ichimoku",   "http://127.0.0.1:5000/api/indicator?symbol=BTC/USD&timeframe=1d&indicator=ichimoku"),
    ("ADX",        "http://127.0.0.1:5000/api/indicator?symbol=BTC/USD&timeframe=1d&indicator=adx"),
    ("Ind List",   "http://127.0.0.1:5000/api/indicator-list"),
]

all_ok = True
for name, url in tests:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read())
            if isinstance(data, list):
                print(f"  {name}: OK - {len(data)} items")
            elif isinstance(data, dict) and 'data' in data:
                print(f"  {name}: OK - render={data.get('render')}, {len(data['data'])} points, series={data.get('series','n/a')}")
            else:
                print(f"  {name}: OK - {json.dumps(data)[:100]}")
    except Exception as e:
        print(f"  {name}: FAIL - {e}")
        all_ok = False

print()
print("ALL TESTS PASSED!" if all_ok else "SOME TESTS FAILED!")
