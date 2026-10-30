from django.apps import AppConfig


class SiteContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "site_content"
    verbose_name = "Контент сайта"

    def ready(self):
        import site_content.signals  # noqa: F401
