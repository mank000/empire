import logging
import time

from django.core.management.base import BaseCommand

from montage_empire.celery import app
from tickets.tasks import dispatch_pending_notifications


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Проверяет ожидающие уведомления, пока работает Celery worker"

    def dispatch_once(self):
        if not app.control.ping(timeout=1):
            return False
        dispatch_pending_notifications.run()
        return True

    def handle(self, *args, **options):
        while True:
            try:
                self.dispatch_once()
            except Exception:
                logger.exception("Не удалось проверить ожидающие уведомления")
            time.sleep(5)
