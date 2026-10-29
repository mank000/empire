from django.db import models
from django.conf import settings
from .phones import normalize_phone


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

    def save(self, *args, **kwargs):
        self.phone_normalized = normalize_phone(self.phone)
        if kwargs.get("update_fields") is not None and "phone" in kwargs["update_fields"]:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"phone_normalized"}
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def __str__(self):
        return f"{self.name} — {self.phone}"
