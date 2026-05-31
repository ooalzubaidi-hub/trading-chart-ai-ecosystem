import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

load_dotenv()

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
crypto_client = CryptoHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

SYMBOLS = {
    "AAPL": {"name": "Apple", "type": "stock"},
    "TSLA": {"name": "Tesla", "type": "stock"},
    "NVDA": {"name": "NVIDIA", "type": "stock"},
    "MSFT": {"name": "Microsoft", "type": "stock"},
    "AMZN": {"name": "Amazon", "type": "stock"},
    "GOOGL": {"name": "Alphabet", "type": "stock"},
    "META": {"name": "Meta Platforms", "type": "stock"},
    "SPY": {"name": "SPDR S&P 500 ETF", "type": "stock"},
    "BTC/USD": {"name": "Bitcoin", "type": "crypto"},
    "ETH/USD": {"name": "Ethereum", "type": "crypto"},
    "SOL/USD": {"name": "Solana", "type": "crypto"}
}

def get_symbol_list():
    return [{"id": k, "name": v["name"], "type": v["type"]} for k, v in SYMBOLS.items()]

_cache = {}

def get_historical_bars(symbol, timeframe, limit=500):
    cache_key = f"{symbol}_{timeframe}_{limit}"
    now = datetime.now().timestamp()
    if cache_key in _cache:
        cached_data, timestamp = _cache[cache_key]
        if now - timestamp < 60:  # 60 seconds cache
            return cached_data

    if symbol not in SYMBOLS:
        print(f"Error: Symbol {symbol} not in predefined list.")
        return []

    asset_type = SYMBOLS[symbol]["type"]
    
    tf_map = {
        "1m": TimeFrame.Minute,
        "5m": TimeFrame(5, TimeFrameUnit.Minute),
        "15m": TimeFrame(15, TimeFrameUnit.Minute),
        "1h": TimeFrame.Hour,
        "1d": TimeFrame.Day
    }
    
    if timeframe not in tf_map:
        print(f"Error: Invalid timeframe {timeframe}.")
        return []
    
    tf = tf_map[timeframe]
    
    # Calculate start time safely to ensure we have enough bars
    days_back = limit
    if timeframe == "1m":
        days_back = (limit / 390) * 2 + 5
    elif timeframe == "5m":
        days_back = (limit / 78) * 2 + 5
    elif timeframe == "15m":
        days_back = (limit / 26) * 2 + 5
    elif timeframe == "1h":
        days_back = (limit / 7) * 2 + 5
    elif timeframe == "1d":
        days_back = limit * 2 + 5
        
    start_time = datetime.now(timezone.utc) - timedelta(days=days_back)
    
    try:
        if asset_type == "stock":
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start_time,
                feed="iex"
            )
            bars = stock_client.get_stock_bars(request_params)
            
            if not bars or bars.df.empty:
                return []
                
            df = bars.df.reset_index()
            
            formatted_bars = []
            for _, row in df.iterrows():
                unix_seconds = int(row['timestamp'].timestamp())
                formatted_bars.append({
                    "time": unix_seconds,
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": float(row['volume'])
                })
        elif asset_type == "crypto":
            import requests
            binance_symbol = symbol.replace("/", "").replace("USD", "USDT")
            binance_url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval={timeframe}&limit={limit}"
            resp = requests.get(binance_url, timeout=10)
            data = resp.json()
            if not isinstance(data, list):
                print(f"Binance error for {symbol}: {data}")
                return []
                
            formatted_bars = []
            for row in data:
                formatted_bars.append({
                    "time": int(row[0] / 1000),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5])
                })
        else:
            return []
            
        formatted_bars = sorted(formatted_bars, key=lambda x: x['time'])
        final_bars = formatted_bars[-limit:]
        _cache[cache_key] = (final_bars, now)
        return final_bars
        
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        _cache[cache_key] = ([], now)
        return []

if __name__ == "__main__":
    print("Fetching AAPL 1d...")
    aapl_bars = get_historical_bars("AAPL", "1d", limit=10)
    print("AAPL first 3 rows:")
    for b in aapl_bars[:3]:
        print(b)
        
    print("\nFetching BTC/USD 1h...")
    btc_bars = get_historical_bars("BTC/USD", "1h", limit=10)
    print("BTC/USD first 3 rows:")
    for b in btc_bars[:3]:
        print(b)
