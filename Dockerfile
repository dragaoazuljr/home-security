FROM python:3.11-slim

RUN apt-get update && apt-get install -y libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
RUN pip install requests python-telegram-bot==13.15 telegramify-markdown telegramify-markdown[mermaid]

WORKDIR /app
COPY . /app

ENV SNAPSHOT_DIR=/app/snapshots
ENV OUTPUT_FILE=/app/history.json

CMD ["python", "main.py"]

