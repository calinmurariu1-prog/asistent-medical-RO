FROM python:3.12-slim

WORKDIR /app

# Fonturi DejaVu — diacritice corecte în PDF-urile exportate.
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
# Ascultă pe $PORT (implicit 8000) — compatibil cu platforme de hosting.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
