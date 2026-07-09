# Dockerfile for Django + Celery + pgvector
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt gunicorn
COPY . .
# Threaded workers: generation requests spend ~3-5s WAITING on the Anthropic
# API (I/O-bound), so threads are near-free concurrency. 3 workers x 8 threads
# = ~24 concurrent requests on the same CPU/RAM (vs. 1 with the bare default).
# --timeout 60 gives headroom over the 30s Anthropic client timeout so a slow
# API call doesn't get the worker killed mid-request (which shows as a 502).
CMD ["gunicorn", "flirty_backend.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--threads", "8", \
     "--worker-class", "gthread", \
     "--timeout", "60", \
     "--graceful-timeout", "10", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
