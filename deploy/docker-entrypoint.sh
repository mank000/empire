#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn mantage_empire.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile - --error-logfile -
