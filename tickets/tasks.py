import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import F, Q
from django.utils import timezone

from .models import NotificationChannelState, NotificationDelivery, NotificationSettings
from .notifications import message_for, send_max, send_telegram


logger = logging.getLogger(__name__)
LEASE = timedelta(minutes=2)
CHANNEL_INTERVAL = timedelta(minutes=1)
DELIVERY_LIFETIME = timedelta(hours=1)
PAUSE_AFTER_FAILURES = 3
FAILURE_PAUSE = timedelta(minutes=15)
MAX_ATTEMPTS = 12


@shared_task(ignore_result=True)
def dispatch_pending_notifications():
    now = timezone.now()
    due = Q(status=NotificationDelivery.Status.PENDING, next_attempt_at__lte=now) | Q(
        status__in=(NotificationDelivery.Status.QUEUED, NotificationDelivery.Status.SENDING),
        lease_until__lte=now,
    )
    # Заявки остаются в админке, но старые уведомления не создают шквал после простоя.
    NotificationDelivery.objects.filter(created_at__lt=now - DELIVERY_LIFETIME).filter(due).update(
        status=NotificationDelivery.Status.EXPIRED, lease_until=None,
    )
    for channel in NotificationDelivery.Channel.values:
        state = NotificationChannelState.objects.get(channel=channel)
        if state.next_allowed_at > now or (state.paused_until and state.paused_until > now):
            continue
        active = NotificationDelivery.objects.filter(
            channel=channel,
            status__in=(NotificationDelivery.Status.QUEUED, NotificationDelivery.Status.SENDING),
            lease_until__gt=now,
        ).exists()
        if active:
            continue
        delivery_id = NotificationDelivery.objects.filter(channel=channel).filter(due).order_by("pk").values_list("pk", flat=True).first()
        if delivery_id is None:
            continue
        claimed = NotificationDelivery.objects.filter(pk=delivery_id).filter(due).update(
            status=NotificationDelivery.Status.QUEUED, lease_until=now + LEASE,
        )
        if not claimed:
            continue
        try:
            send_notification.apply_async(args=(delivery_id,), retry=False)
        except Exception as exc:
            NotificationDelivery.objects.filter(pk=delivery_id, status=NotificationDelivery.Status.QUEUED).update(
                status=NotificationDelivery.Status.PENDING,
                lease_until=None,
                next_attempt_at=timezone.now() + timedelta(seconds=30),
                last_error=type(exc).__name__,
            )
            logger.error("Не удалось поставить уведомление %s в очередь: %s", delivery_id, type(exc).__name__)


@shared_task(ignore_result=True, rate_limit="1/s")
def send_notification(delivery_id):
    now = timezone.now()
    claimed = NotificationDelivery.objects.filter(
        pk=delivery_id, status=NotificationDelivery.Status.QUEUED, lease_until__gt=now,
    ).update(status=NotificationDelivery.Status.SENDING, lease_until=now + LEASE)
    if not claimed:
        return
    delivery = NotificationDelivery.objects.select_related("ticket").get(pk=delivery_id)
    if delivery.created_at < now - DELIVERY_LIFETIME:
        NotificationDelivery.objects.filter(pk=delivery_id).update(
            status=NotificationDelivery.Status.EXPIRED, lease_until=None,
        )
        return
    config = NotificationSettings.objects.get(pk=1)
    enabled = config.telegram_enabled if delivery.channel == NotificationDelivery.Channel.TELEGRAM else config.max_enabled
    if not enabled:
        NotificationDelivery.objects.filter(pk=delivery_id).update(
            status=NotificationDelivery.Status.SKIPPED, lease_until=None,
        )
        return

    state = NotificationChannelState.objects.get(channel=delivery.channel)
    reserved = NotificationChannelState.objects.filter(channel=delivery.channel, next_allowed_at__lte=now).filter(
        Q(paused_until__isnull=True) | Q(paused_until__lte=now)
    ).update(next_allowed_at=now + CHANNEL_INTERVAL)
    if not reserved:
        retry_at = max(state.next_allowed_at, state.paused_until or now, now + timedelta(seconds=5))
        NotificationDelivery.objects.filter(pk=delivery_id).update(
            status=NotificationDelivery.Status.PENDING, next_attempt_at=retry_at, lease_until=None,
        )
        return

    NotificationDelivery.objects.filter(pk=delivery_id).update(attempts=F("attempts") + 1)
    delivery.refresh_from_db(fields=["attempts"])
    try:
        token = config.token_for(delivery.channel)
        chat_id = config.telegram_chat_id if delivery.channel == NotificationDelivery.Channel.TELEGRAM else config.max_chat_id
        if not token or not chat_id:
            raise ValueError("Отсутствует токен или ID чата")
        message = message_for(delivery.ticket)
        if delivery.channel == NotificationDelivery.Channel.TELEGRAM:
            send_telegram(token, chat_id, message)
        else:
            send_max(token, chat_id, message)
    except Exception as exc:
        state.consecutive_failures += 1
        if state.consecutive_failures >= PAUSE_AFTER_FAILURES:
            state.paused_until = timezone.now() + FAILURE_PAUSE
        state.save(update_fields=["consecutive_failures", "paused_until"])
        final = delivery.attempts >= MAX_ATTEMPTS
        NotificationDelivery.objects.filter(pk=delivery_id).update(
            status=NotificationDelivery.Status.FAILED if final else NotificationDelivery.Status.PENDING,
            next_attempt_at=timezone.now() + timedelta(seconds=min(2 ** delivery.attempts, 300)),
            lease_until=None,
            last_error=type(exc).__name__,
        )
        # Исключения клиентов могут содержать токен или телефон: пишем только тип.
        logger.error("Не удалось отправить уведомление %s через %s: %s", delivery_id, delivery.channel, type(exc).__name__)
        return
    state.consecutive_failures = 0
    state.paused_until = None
    state.save(update_fields=["consecutive_failures", "paused_until"])
    NotificationDelivery.objects.filter(pk=delivery_id).update(
        status=NotificationDelivery.Status.SENT,
        sent_at=timezone.now(), lease_until=None, last_error="",
    )
