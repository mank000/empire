from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .content import HOME_KEY, SETTINGS_KEY
from .models import Case, CustomerLogo, FAQ, SiteSettings


@receiver([post_save, post_delete], sender=SiteSettings)
def invalidate_settings(sender, **kwargs):
    cache.delete(SETTINGS_KEY)
    transaction.on_commit(lambda: cache.delete(SETTINGS_KEY))


@receiver([post_save, post_delete], sender=Case)
@receiver([post_save, post_delete], sender=FAQ)
@receiver([post_save, post_delete], sender=CustomerLogo)
def invalidate_home(sender, **kwargs):
    cache.delete(HOME_KEY)
    transaction.on_commit(lambda: cache.delete(HOME_KEY))
