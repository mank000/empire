import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.shortcuts import render
from django.db import connection, transaction
from django.utils import timezone

from tickets.forms import TicketForm
from tickets.models import NotificationDelivery, NotificationSettings, Ticket
from site_content.content import get_home_content

logger = logging.getLogger(__name__)


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        logger.exception("Проверка базы данных не прошла")
        return HttpResponse(status=503)
    return HttpResponse("ok", content_type="text/plain")


def home(request):
    content = get_home_content()
    middle = (len(content["faq_items"]) + 1) // 2
    return render(request, "home.html", {
        "public_site_url": settings.PUBLIC_SITE_URL,
        **content,
        "faq_left": content["faq_items"][:middle],
        "faq_right": content["faq_items"][middle:],
    })


def privacy_policy(request):
    return render(request, "privacy-policy.html")


def requisites(request):
    return render(request, "requisites.html")


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
