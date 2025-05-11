import asyncio
import json
import websockets
from confluent_kafka import Producer

producer = Producer({'bootstrap.servers': 'localhost:9092'})

async def bybit_listener():
    url = "wss://stream.bybit.com/v5/public/spot"
    async with websockets.connect(url) as websocket:
        await websocket.send(json.dumps({
            "op": "subscribe",
            "args": ["publicTrade.BTCUSDT"]
        }))
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)
            
            if data.get("topic", "").startswith("publicTrade"):
                producer.produce("bybit_trades", key="BTCUSDT", value=json.dumps(data))
                producer.flush()

asyncio.run(bybit_listener())
