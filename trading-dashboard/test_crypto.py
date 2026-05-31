import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from alpaca.data.live import CryptoDataStream

# Enable debugging logs for alpaca
logging.basicConfig(level=logging.DEBUG)

load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

async def handler(trade):
    print("Received trade:", trade)
    sys.stdout.flush()

def test_crypto():
    print("Testing Crypto...")
    try:
        stream = CryptoDataStream(ALPACA_API_KEY, ALPACA_SECRET_KEY)
        stream.subscribe_trades(handler, "BTC/USD")
        stream.run()
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test_crypto()
