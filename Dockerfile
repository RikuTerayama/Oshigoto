FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    fonts-unifont \
    fonts-dejavu \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE $PORT

CMD gunicorn --bind 0.0.0.0:$PORT \
  --workers ${WEB_CONCURRENCY:-1} \
  --threads ${WEB_THREADS:-1} \
  --worker-class sync \
  --timeout ${WEB_TIMEOUT:-180} \
  --graceful-timeout ${WEB_GRACEFUL_TIMEOUT:-30} \
  --keep-alive ${WEB_KEEPALIVE:-5} \
  --max-requests ${WEB_MAX_REQUESTS:-500} \
  --max-requests-jitter ${WEB_MAX_REQUESTS_JITTER:-50} \
  --access-logfile - \
  --error-logfile - \
  --log-level ${WEB_LOG_LEVEL:-warning} \
  --log-file - \
  --capture-output \
  --enable-stdio-inheritance \
  app:app
