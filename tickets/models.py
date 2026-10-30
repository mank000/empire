from django.db import models
from django.conf import settings
from django.utils import timezone

from .phones import normalize_phone
from .secrets import decrypt_token


class Ticket(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В работе"
        CLOSED = "closed", "Закрыта"

    name = models.CharField("Имя", max_length=100)
    phone = models.CharField("Телефон", max_length=25)
    phone_normalized = models.CharField("Телефон для поиска", max_length=12, blank=True, db_index=True)
    status = models.CharField("Статус", max_length=20, choices=Status.choices, default=Status.NEW)
    manager_comment = models.TextField("Комментарий менеджера", blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Ответственный менеджер",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_tickets",
    )
    created_at = models.DateTimeField("Получена", auto_now_add=True)
    consent_at = models.DateTimeField("Согласие получено", null=True, blank=True)

    def save(self, *args, **kwargs):
        self.phone_normalized = normalize_phone(self.phone)
        if self.phone_normalized:
            self.phone = self.phone_normalized
        if kwargs.get("update_fields") is not None and "phone" in kwargs["update_fields"]:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"phone_normalized"}
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def __str__(self):
        return f"{self.name} — {self.phone}"


class NotificationSettings(models.Model):
    telegram_enabled = models.BooleanField("Отправлять в Telegram", default=False)
    telegram_chat_id = models.CharField("ID чата Telegram", max_length=100, blank=True)
    telegram_token_encrypted = models.TextField("Токен Telegram", blank=True, editable=False)
    max_enabled = models.BooleanField("Отправлять в MAX", default=False)
    max_chat_id = models.CharField("ID чата MAX", max_length=100, blank=True)
    max_token_encrypted = models.TextField("Токен MAX", blank=True, editable=False)
    email_enabled = models.BooleanField("Отправлять на почту", default=False)
    email_recipient = models.EmailField("Почта получателя", blank=True)

    class Meta:
        verbose_name = "Настройки уведомлений"
        verbose_name_plural = "Настройки уведомлений"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def token_for(self, channel):
        encrypted = self.telegram_token_encrypted if channel == NotificationDelivery.Channel.TELEGRAM else self.max_token_encrypted
        return decrypt_token(encrypted) if encrypted else ""

    def __str__(self):
        return "Настройки уведомлений"


class NotificationDelivery(models.Model):
    class Channel(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        MAX = "max", "MAX"
        EMAIL = "email", "Почта"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        QUEUED = "queued", "В очереди"
        SENDING = "sending", "Отправляется"
        SENT = "sent", "Отправлено"
        FAILED = "failed", "Ошибка"
        SKIPPED = "skipped", "Отключено"
        SUMMARIZED = "summarized", "В сводке"

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="notifications", verbose_name="Заявка")
    channel = models.CharField("Канал", max_length=10, choices=Channel.choices)
    status = models.CharField("Состояние", max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField("Попыток", default=0)
    next_attempt_at = models.DateTimeField("Следующая попытка", default=timezone.now)
    lease_until = models.DateTimeField("Срок обработки", null=True, blank=True)
    sent_at = models.DateTimeField("Отправлено", null=True, blank=True)
    last_error = models.CharField("Последняя ошибка", max_length=100, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Доставка уведомления"
        verbose_name_plural = "Доставка уведомлений"
        constraints = [models.UniqueConstraint(fields=["ticket", "channel"], name="unique_ticket_notification_channel")]
        indexes = [models.Index(fields=["status", "next_attempt_at"])]

    def __str__(self):
        return f"{self.get_channel_display()} · заявка #{self.ticket_id}"


class NotificationChannelState(models.Model):
    channel = models.CharField("Канал", max_length=10, choices=NotificationDelivery.Channel.choices, unique=True)
    next_allowed_at = models.DateTimeField("Следующая отправка", default=timezone.now)
    paused_until = models.DateTimeField("Пауза до", null=True, blank=True)
    consecutive_failures = models.PositiveSmallIntegerField("Ошибок подряд", default=0)

    class Meta:
        verbose_name = "Ограничение канала уведомлений"
        verbose_name_plural = "Ограничения каналов уведомлений"

    def __str__(self):
        return self.get_channel_display()
