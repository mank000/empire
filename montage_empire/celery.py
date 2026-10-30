import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "montage_empire.settings")

app = Celery("montage_empire")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
