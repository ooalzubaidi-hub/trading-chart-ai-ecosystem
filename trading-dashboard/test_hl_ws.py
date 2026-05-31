import asyncio
import websockets
import json

async def test_hl():
    uri = "wss://api.hyperliquid.xyz/ws"
    async with websockets.connect(uri) as ws:
        sub_msg = {
            "method": "subscribe",
            "subscription": {"type": "candle", "coin": "BTC", "interval": "1m"}
        }
        await ws.send(json.dumps(sub_msg))
        
        # Wait for subscriptionResponse
        resp = await ws.recv()
        print("MSG 1:", resp)
        
        # Wait for first candle message
        msg2 = await ws.recv()
        print("MSG 2:", msg2)
        
        # Wait for another one just in case
        msg3 = await ws.recv()
        print("MSG 3:", msg3)

asyncio.run(test_hl())
