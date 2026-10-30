import os

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

DEV_PREFIX = "dev-plaintext:"


def _cipher():
    key = os.getenv("NOTIFICATION_ENCRYPTION_KEY")
    if not key:
        raise ImproperlyConfigured("NOTIFICATION_ENCRYPTION_KEY не задан")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ImproperlyConfigured("NOTIFICATION_ENCRYPTION_KEY должен быть ключом Fernet") from exc


def encrypt_token(value):
    if settings.DEBUG:
        return DEV_PREFIX + value
    return _cipher().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_token(value):
    if value.startswith(DEV_PREFIX):
        if settings.DEBUG:
            return value[len(DEV_PREFIX):]
        raise ImproperlyConfigured("Токен из dev нельзя использовать в production")
    return _cipher().decrypt(value.encode("ascii")).decode("utf-8")
