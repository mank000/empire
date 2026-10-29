from django import forms
from django.contrib import admin
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils import timezone

from .models import NotificationChannelState, NotificationDelivery, NotificationSettings, Ticket
from .phones import normalize_phone
from .secrets import DEV_PREFIX, encrypt_token


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "phone", "status", "assignee", "consent_at")
    list_filter = ("status", "assignee")
    search_fields = ("name", "phone", "phone_normalized")
    readonly_fields = ("name", "phone", "phone_normalized", "created_at", "consent_at")
    actions = ("take_in_progress",)

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        return fields if request.user.is_superuser else (*fields, "assignee")

    def save_model(self, request, obj, form, change):
        if obj.status != Ticket.Status.NEW and obj.assignee_id is None:
            obj.assignee = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Взять выбранные заявки в работу")
    def take_in_progress(self, request, queryset):
        count = queryset.filter(status=Ticket.Status.NEW, assignee__isnull=True).update(
            status=Ticket.Status.IN_PROGRESS, assignee=request.user,
        )
        self.message_user(request, f"Взято в работу: {count}")

    def get_search_results(self, request, queryset, search_term):
        results, distinct = super().get_search_results(request, queryset, search_term)
        normalized = normalize_phone(search_term)
        if normalized:
            results = results | queryset.filter(Q(phone_normalized=normalized))
        return results, distinct


class NotificationSettingsForm(forms.ModelForm):
    telegram_token = forms.CharField(
        label="Новый токен Telegram", required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Оставьте пустым, чтобы сохранить текущий токен.",
    )
    clear_telegram_token = forms.BooleanField(label="Удалить токен Telegram", required=False)
    max_token = forms.CharField(
        label="Новый токен MAX", required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Оставьте пустым, чтобы сохранить текущий токен.",
    )
    clear_max_token = forms.BooleanField(label="Удалить токен MAX", required=False)

    class Meta:
        model = NotificationSettings
        fields = ("telegram_enabled", "telegram_chat_id", "max_enabled", "max_chat_id", "email_enabled", "email_recipient")

    def clean(self):
        data = super().clean()
        for channel in ("telegram", "max"):
            new_token = data.get(f"{channel}_token")
            clear_token = data.get(f"clear_{channel}_token")
            old_token = getattr(self.instance, f"{channel}_token_encrypted")
            chat_id = data.get(f"{channel}_chat_id")
            if new_token and clear_token:
                self.add_error(f"{channel}_token", "Нельзя одновременно задать и удалить токен.")
            if new_token:
                try:
                    encrypt_token(new_token)
                except ImproperlyConfigured as exc:
                    self.add_error(f"{channel}_token", str(exc))
            if data.get(f"{channel}_enabled") and (not (new_token or old_token) or clear_token or not chat_id):
                self.add_error(f"{channel}_enabled", "Для отправки укажите токен и ID чата.")
            if data.get(f"{channel}_enabled") and not settings.DEBUG and old_token.startswith(DEV_PREFIX) and not new_token:
                self.add_error(f"{channel}_token", "Токен из dev нужно заменить перед production.")
            if chat_id:
                try:
                    int(chat_id)
                except ValueError:
                    self.add_error(f"{channel}_chat_id", "ID чата должен быть числом.")
        if data.get("email_enabled") and not data.get("email_recipient"):
            self.add_error("email_recipient", "Укажите адрес получателя.")
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        for channel in ("telegram", "max"):
            new_token = self.cleaned_data.get(f"{channel}_token")
            if new_token:
                setattr(instance, f"{channel}_token_encrypted", encrypt_token(new_token))
            elif self.cleaned_data.get(f"clear_{channel}_token"):
                setattr(instance, f"{channel}_token_encrypted", "")
        if commit:
            instance.save()
        return instance


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    form = NotificationSettingsForm
    fieldsets = (
        ("Telegram", {"fields": ("telegram_enabled", "telegram_chat_id", "telegram_token", "clear_telegram_token", "telegram_token_is_set")}),
        ("MAX", {"fields": ("max_enabled", "max_chat_id", "max_token", "clear_max_token", "max_token_is_set")}),
        ("Почта", {"fields": ("email_enabled", "email_recipient")}),
    )
    readonly_fields = ("telegram_token_is_set", "max_token_is_set")

    @admin.display(boolean=True, description="Токен Telegram задан")
    def telegram_token_is_set(self, obj):
        return bool(obj and obj.telegram_token_encrypted)

    @admin.display(boolean=True, description="Токен MAX задан")
    def max_token_is_set(self, obj):
        return bool(obj and obj.max_token_encrypted)

    def has_add_permission(self, request):
        return request.user.is_superuser and not NotificationSettings.objects.exists()

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("ticket", "channel", "status", "attempts", "next_attempt_at", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("ticket__name", "ticket__phone")
    readonly_fields = ("ticket", "channel", "status", "attempts", "next_attempt_at", "lease_until", "sent_at", "last_error", "created_at")
    actions = ("retry_delivery",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.action(description="Повторить выбранные неудачные доставки")
    def retry_delivery(self, request, queryset):
        count = queryset.filter(status__in=(NotificationDelivery.Status.FAILED, NotificationDelivery.Status.SKIPPED)).update(
            status=NotificationDelivery.Status.PENDING, attempts=0,
            next_attempt_at=timezone.now(), lease_until=None, last_error="",
        )
        self.message_user(request, f"Поставлено на повторную отправку: {count}")


@admin.register(NotificationChannelState)
class NotificationChannelStateAdmin(admin.ModelAdmin):
    list_display = ("channel", "next_allowed_at", "paused_until", "consecutive_failures")
    readonly_fields = list_display

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
