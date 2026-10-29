from django.contrib import admin

from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "phone", "consent_at")
    search_fields = ("name", "phone")
    readonly_fields = ("name", "phone", "created_at", "consent_at")
