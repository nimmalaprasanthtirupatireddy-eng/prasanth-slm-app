FROM node:20-slim AS builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY models/ ./models/
COPY --from=builder /app/static ./static

ENV PYTHONUNBUFFERED=1
# Render and many other platforms provide a PORT env var
ENV PORT=7860

EXPOSE 7860

CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
