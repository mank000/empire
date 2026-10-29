FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py ./
COPY mantage_empire ./mantage_empire
COPY tickets ./tickets
COPY templates ./templates
COPY static ./static
COPY deploy/docker-entrypoint.sh ./deploy/docker-entrypoint.sh
COPY deploy/backup_database.py ./deploy/backup_database.py
COPY deploy/restore_database.py ./deploy/restore_database.py

RUN chmod +x ./deploy/docker-entrypoint.sh

EXPOSE 8000

FROM base AS prod
CMD ["./deploy/docker-entrypoint.sh"]

FROM base AS dev
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
CMD ["sh", "-c", "python manage.py migrate --noinput && exec python manage.py runserver 0.0.0.0:8000"]
