FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DJANGO_DEBUG=1 \
    DJANGO_SECRET_KEY=build-only-not-used-at-runtime \
    POSTGRES_PASSWORD=build-only-not-used-at-runtime \
    python manage.py collectstatic --noinput
CMD ["sh","-c","python manage.py portal_preflight && python manage.py migrate --fake-initial --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60 --access-logfile - --error-logfile -"]
