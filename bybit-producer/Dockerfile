FROM python:3.10-slim

WORKDIR /app
COPY bybit_producer.py .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "bybit_producer.py"]
