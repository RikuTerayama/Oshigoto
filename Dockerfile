FROM python:3.11.15-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app

WORKDIR /app

COPY requirements.lock.txt .
RUN python -m pip install --require-hashes --only-binary=:all: -r requirements.lock.txt

# Application source remains root-owned and read-only to the runtime user.
COPY . .

USER 10001:10001

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
  --limit-request-line 4094 \
  --limit-request-fields 50 \
  --limit-request-field_size 8190 \
  --access-logfile - \
  --error-logfile - \
  --log-level ${WEB_LOG_LEVEL:-warning} \
  --capture-output \
  app:app
