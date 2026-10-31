from functools import lru_cache

from django.conf import settings
from PIL import Image


@lru_cache(maxsize=64)
def static_image_dimensions(path):
    root = (settings.BASE_DIR / "static").resolve()
    image_path = (root / path).resolve()
    if not image_path.is_relative_to(root):
        return 1, 1
    try:
        with Image.open(image_path) as image:
            return image.size
    except (OSError, ValueError):
        return 1, 1


def image_dimensions(upload, initial_image):
    if upload:
        try:
            return upload.width, upload.height
        except (OSError, ValueError):
            pass
    return static_image_dimensions(initial_image)
