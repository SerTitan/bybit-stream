import asyncio
import json
import os
import socket
import time
import websockets
from confluent_kafka import Producer

def wait_kafka(host: str, port: int, timeout: int = 60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), 3):
                print(f"[producer] Kafka {host}:{port} reachable")
                return
        except OSError:
            print("[producer] Kafka not up yet, retry…")
            time.sleep(1)
    raise RuntimeError(f"Kafka {host}:{port} not reachable after {timeout}s")

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "bybit_trades")
producer = Producer({"bootstrap.servers": BOOTSTRAP})

async def main():
    host, port = BOOTSTRAP.split(":")
    wait_kafka(host, int(port))

    url = "wss://stream.bybit.com/v5/public/spot"
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"op": "subscribe", "args": ["publicTrade.BTCUSDT"]}))
        print("[producer] subscribed, streaming…")

        while True:
            msg = await ws.recv()
            producer.produce(TOPIC, key="BTCUSDT", value=msg.encode("utf-8"))
            producer.poll(0)

if __name__ == "__main__":
    asyncio.run(main())
