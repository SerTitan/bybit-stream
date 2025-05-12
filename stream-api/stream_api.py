# stream_api.py
import asyncio
import os
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from confluent_kafka import Consumer

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "bybit_avg")

message_queue = asyncio.Queue()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(connection)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    threading.Thread(target=kafka_consumer_thread, args=(loop,), daemon=True).start()

def kafka_consumer_thread(loop):
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP,
        'group.id': 'stream-api-consumer',
        'auto.offset.reset': 'latest'
    })

    consumer.subscribe([TOPIC])
    print("[StreamAPI] Kafka consumer запущен...")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"[StreamAPI] Kafka error: {msg.error()}")
                continue

            text = msg.value().decode("utf-8")
            print(f"[StreamAPI] New message: {text}")
            asyncio.run_coroutine_threadsafe(message_queue.put(text), loop)

    finally:
        consumer.close()

@app.get("/")
async def root():
    return {"message": "StreamAPI is running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            message = await message_queue.get()
            await manager.broadcast(message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
