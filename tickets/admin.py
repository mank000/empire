from django.contrib import admin
from django.db.models import Q

from .models import Ticket
from .phones import normalize_phone


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "phone", "status", "assignee")
    list_filter = ("status", "assignee")
    search_fields = ("name", "phone", "phone_normalized")
    readonly_fields = ("name", "phone", "phone_normalized", "created_at")
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
