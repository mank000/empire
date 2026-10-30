import json
import logging

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import TicketForm
from .models import NotificationDelivery, NotificationSettings, Ticket

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
    form = TicketForm(data)
    if not form.is_valid():
        return JsonResponse({"success": False, "errors": form.errors.get_json_data()}, status=400)

    try:
        with transaction.atomic():
            ticket = Ticket.objects.create(
                name=form.cleaned_data["name"], phone=form.cleaned_data["phone"],
                consent_at=timezone.now(),
            )
            config = NotificationSettings.objects.filter(pk=1).first()
            if config:
                for channel, enabled in (
                    (NotificationDelivery.Channel.TELEGRAM, config.telegram_enabled),
                    (NotificationDelivery.Channel.MAX, config.max_enabled),
                    (NotificationDelivery.Channel.EMAIL, config.email_enabled),
                ):
                    if enabled:
                        NotificationDelivery.objects.create(ticket=ticket, channel=channel)
    except Exception:
        logger.exception("Не удалось сохранить заявку")
        return JsonResponse({"success": False, "error": "Не удалось принять заявку. Попробуйте позже."}, status=503)
    return JsonResponse({"success": True, "ticket_id": ticket.pk}, status=201)
