from django.core.cache import cache

from .models import Case, CustomerLogo, FAQ, SiteSettings


SETTINGS_KEY = "site-content:settings:v1"
HOME_KEY = "site-content:home:v1"
CACHE_SECONDS = 300


def get_site_settings():
    value = cache.get(SETTINGS_KEY)
    if value is None:
        value = SiteSettings.objects.filter(pk=1).first()
        if value is not None:
            cache.set(SETTINGS_KEY, value, CACHE_SECONDS)
    return value


def get_home_content():
    value = cache.get(HOME_KEY)
    if value is None:
        value = {
            "cases": list(Case.objects.filter(is_visible=True)),
            "faq_items": list(FAQ.objects.filter(is_visible=True)),
            "customer_logos": list(CustomerLogo.objects.filter(is_visible=True)),
        }
        cache.set(HOME_KEY, value, CACHE_SECONDS)
    return value
