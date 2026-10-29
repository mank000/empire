from django.contrib import admin
from django.db.models import Q

from .models import Ticket
from .phones import normalize_phone


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "phone", "status")
    list_filter = ("status",)
    search_fields = ("name", "phone", "phone_normalized")
    readonly_fields = ("name", "phone", "phone_normalized", "created_at")

    def get_search_results(self, request, queryset, search_term):
        results, distinct = super().get_search_results(request, queryset, search_term)
        normalized = normalize_phone(search_term)
        if normalized:
            results = results | queryset.filter(Q(phone_normalized=normalized))
        return results, distinct
