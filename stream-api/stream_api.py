import asyncio
import os
import threading
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from confluent_kafka import Consumer
import psycopg2

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "bybit_avg")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "bybitdb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "bybit")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "bybitpass")

message_queue = asyncio.Queue()

def get_db_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
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
    print("[StreamAPI] Kafka consumer started")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"[StreamAPI] Kafka error: {msg.error()}")
                continue

            text = msg.value().decode("utf-8")
            asyncio.run_coroutine_threadsafe(message_queue.put(text), loop)
    finally:
        consumer.close()

@app.get("/")
async def root():
    return {"message": "StreamAPI running"}

@app.get("/history")
async def get_history(request: Request):
    now_utc = datetime.utcnow()
    end = now_utc.replace(second=0, microsecond=0)
    start = end - timedelta(minutes=1)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT symbol, price, timestamp 
            FROM trades 
            WHERE timestamp >= %s AND timestamp < %s
            ORDER BY timestamp
        """, (start, end))
        rows = cur.fetchall()

        results = [f"{row[0]} avg: {row[1]:.2f}" for row in rows]
        return JSONResponse(content={
            "time_range": f"{start.strftime('%H:%M:%S')} to {end.strftime('%H:%M:%S')}",
            "data": results,
            "debug_info": {
                "queried_period": f"from {start} to {end}",
                "found_records": len(results),
                "server_time": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        cur.close()
        conn.close()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            message = await message_queue.get()
            await manager.broadcast(message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
