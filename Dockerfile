FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=superrecord.settings

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    libcairo2-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media /app/staticfiles /app/logs

RUN SECRET_KEY=build-only-key DATABASE_URL= \
    python manage.py collectstatic --noinput --clear 2>&1 || echo 'collectstatic skipped'

RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

CMD ["bash", "/app/start.sh"]
