"""Check that Gunicorn answers and the database is available."""

import os
from urllib.request import Request, urlopen


hosts = [value.strip() for value in os.environ["DJANGO_ALLOWED_HOSTS"].split(",")]
host = next((value.lstrip(".") for value in hosts if value and value != "*"), "localhost")
request = Request("http://127.0.0.1:8000/health/", headers={"Host": host, "X-Forwarded-Proto": "https"})
with urlopen(request, timeout=3) as response:
    if response.status != 200:
        raise SystemExit(1)
