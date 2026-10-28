import json
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from tickets.forms import TicketForm
from tickets.models import Ticket

logger = logging.getLogger(__name__)


@require_POST
def create_ticket(request):
    if request.content_type != "application/json":
        return JsonResponse({"success": False, "error": "Ожидается JSON."}, status=415)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"success": False, "error": "Некорректный JSON."}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"success": False, "error": "Ожидается объект JSON."}, status=400)
    form = TicketForm(data)  # Правила проверки вынесены в отдельную форму.
    if not form.is_valid():
        return JsonResponse({"success": False, "errors": form.errors.get_json_data()}, status=400)

    # Отсекаем случайный двойной клик и повторные заявки с одного адреса.
    address = request.META.get("REMOTE_ADDR", "unknown")
    throttle_key = f"ticket-submit:{address}"
    if not cache.add(throttle_key, True, timeout=30):
        return JsonResponse({"success": False, "error": "Подождите 30 секунд перед повторной заявкой."}, status=429)

    try:
        ticket = Ticket.objects.create(
            name=form.cleaned_data["name"], phone=form.cleaned_data["phone"]
        )
    except Exception:
        cache.delete(throttle_key)
        logger.exception("Не удалось проверить или сохранить заявку")
        return JsonResponse({"success": False, "error": "Не удалось принять заявку. Попробуйте позже."}, status=503)
    return JsonResponse({"success": True, "ticket_id": ticket.pk}, status=201)
