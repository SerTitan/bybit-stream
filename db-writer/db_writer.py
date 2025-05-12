import os
import json
import time
from datetime import datetime
from confluent_kafka import Consumer
import psycopg2

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "bybit_avg")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "bybitdb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "bybit")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "bybitpass")

def get_db_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )

def create_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            symbol TEXT NOT NULL,
            price FLOAT NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def main():
    create_table()
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP,
        'group.id': 'db-writer',
        'auto.offset.reset': 'latest'
    })
    consumer.subscribe([TOPIC])

    buffer = []
    last_flush = time.time()

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Kafka error: {msg.error()}")
                continue

            text = msg.value().decode("utf-8")
            print(f"New message: {text}")
            try:
                symbol, price_str = text.split(" avg: ")
                price = float(price_str)
                timestamp = datetime.utcnow()  # Убрали округление до минут
                buffer.append((timestamp, symbol, price))
            except Exception as e:
                print(f"Parse error: {e}")

            if time.time() - last_flush >= 60:
                if buffer:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.executemany(
                        "INSERT INTO trades (timestamp, symbol, price) VALUES (%s, %s, %s)",
                        buffer
                    )
                    conn.commit()
                    cur.close()
                    conn.close()
                    print(f"Flushed {len(buffer)} records to DB.")
                    buffer.clear()
                last_flush = time.time()
    finally:
        consumer.close()

if __name__ == "__main__":
    main()
