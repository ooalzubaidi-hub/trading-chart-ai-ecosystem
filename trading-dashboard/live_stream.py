import threading
import asyncio
import os
import atexit
import time
from dotenv import load_dotenv
from alpaca.data.live import StockDataStream, CryptoDataStream
from alpaca.data.enums import DataFeed

load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

latest_prices = {}
stream_status = {"crypto": "disconnected", "stock": "disconnected"}

_streams_started = False
crypto_stream_instance = None
stock_stream_instance = None

async def handle_trade(trade):
    # alpaca-py trade object has symbol, price, timestamp
    symbol = trade.symbol
    price = float(trade.price)
    # the timestamp is a pandas Timestamp or datetime object with timezone
    unix_time = int(trade.timestamp.timestamp())
    print(f"Trade received: {symbol} @ {price}")
    latest_prices[symbol] = {
        "price": price,
        "time": unix_time
    }

async def handle_quote(quote):
    symbol = quote.symbol
    mid_price = (float(quote.bid_price) + float(quote.ask_price)) / 2
    unix_time = int(quote.timestamp.timestamp())
    
    current = latest_prices.get(symbol)
    if not current or unix_time >= current["time"]:
        latest_prices[symbol] = {
            "price": mid_price,
            "time": unix_time
        }

def run_crypto_stream():
    global crypto_stream_instance
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            crypto_stream_instance = CryptoDataStream(ALPACA_API_KEY, ALPACA_SECRET_KEY)
            crypto_stream_instance.subscribe_trades(handle_trade, "BTC/USD", "ETH/USD", "SOL/USD")
            crypto_stream_instance.subscribe_quotes(handle_quote, "BTC/USD", "ETH/USD", "SOL/USD")
            print("Starting Crypto stream...")
            stream_status["crypto"] = "connected"
            crypto_stream_instance.run()
        except Exception as e:
            stream_status["crypto"] = "error"
            print(f"Crypto stream error: {e}, reconnecting in 5s...")
            time.sleep(5)

def run_stock_stream():
    global stock_stream_instance
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            stock_stream_instance = StockDataStream(ALPACA_API_KEY, ALPACA_SECRET_KEY, feed=DataFeed.IEX)
            # Stock symbols used in our app
            stock_stream_instance.subscribe_trades(handle_trade, "AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "SPY")
            print("Starting Stock stream...")
            stream_status["stock"] = "connected"
            stock_stream_instance.run()
        except Exception as e:
            stream_status["stock"] = "error"
            print(f"Stock stream error: {e}, reconnecting in 5s...")
            time.sleep(5)

def start_streams():
    global _streams_started
    if _streams_started:
        print("Streams already started, ignoring.")
        return
    _streams_started = True

    # Disable Alpaca crypto websocket as it causes HTTP 429 rate limit death spirals
    # crypto_thread = threading.Thread(target=run_crypto_stream, daemon=True)
    stock_thread = threading.Thread(target=run_stock_stream, daemon=True)
    
    # crypto_thread.start()
    stock_thread.start()

def stop_streams():
    print("Stopping Alpaca streams...")
    try:
        if crypto_stream_instance:
            # Running stop_ws() in an event loop if needed, but stop_ws is typically a normal method.
            # Depending on alpaca-py version, it might be an async method, but usually it's safe to call directly
            crypto_stream_instance.stop()
    except Exception as e:
        print(f"Error stopping crypto: {e}")
    try:
        if stock_stream_instance:
            stock_stream_instance.stop()
    except Exception as e:
        print(f"Error stopping stock: {e}")

atexit.register(stop_streams)

def get_latest_prices():
    now = int(time.time())
    result = {}
    for sym, data in latest_prices.items():
        result[sym] = {
            "price": data["price"],
            "time": data["time"],
            "last_trade_age": now - data["time"]
        }
    result["stream_status"] = stream_status
    return result
