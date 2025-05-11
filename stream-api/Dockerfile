FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY stream_api.py .
COPY static ./static

CMD ["uvicorn", "stream_api:app", "--host", "0.0.0.0", "--port", "8000"]
