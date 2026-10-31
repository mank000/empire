import logging

from django.db import connection
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        logger.exception("Проверка базы данных не прошла")
        return HttpResponse(status=503)
    return HttpResponse("ok", content_type="text/plain")
