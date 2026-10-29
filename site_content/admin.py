from django.contrib import admin

from .models import Case, CustomerLogo, FAQ, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Контакты", {"fields": ("phone", "work_hours", "email", "address", "telegram_url", "whatsapp_url")}),
        ("Реквизиты", {"fields": ("legal_name", "inn", "ogrn")}),
        ("Поисковые системы", {"fields": ("seo_title", "seo_description")}),
        ("Политика", {"fields": ("privacy_policy",)}),
    )

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_visible")
    list_editable = ("order", "is_visible")
    list_filter = ("is_visible",)
    search_fields = ("title", "description", "tags")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "order", "is_visible")
    list_editable = ("order", "is_visible")
    list_filter = ("is_visible",)
    search_fields = ("question", "answer")


@admin.register(CustomerLogo)
class CustomerLogoAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_visible")
    list_editable = ("order", "is_visible")
    list_filter = ("is_visible",)
