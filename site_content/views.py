from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from .content import get_home_content


def home(request):
    content = get_home_content()
    middle = (len(content["faq_items"]) + 1) // 2
    return render(request, "home.html", {
        "public_site_url": settings.PUBLIC_SITE_URL,
        **content,
        "faq_left": content["faq_items"][:middle],
        "faq_right": content["faq_items"][middle:],
    })


def privacy_policy(request):
    return render(request, "privacy-policy.html")


def requisites(request):
    return render(request, "requisites.html")


def not_found(request, exception=None):
    return render(request, "404.html", status=404)


def absolute_public_url(request, route_name):
    path = reverse(route_name)
    if settings.PUBLIC_SITE_URL:
        return f"{settings.PUBLIC_SITE_URL}{path}"
    return request.build_absolute_uri(path)


def robots_txt(request):
    sitemap_url = absolute_public_url(request, "sitemap")
    return HttpResponse(
        f"User-agent: *\nDisallow: /admin/\nSitemap: {sitemap_url}\n",
        content_type="text/plain; charset=utf-8",
    )


def sitemap_xml(request):
    urls = ("home", "privacy_policy", "requisites")
    entries = "".join(
        f"  <url><loc>{escape(absolute_public_url(request, name))}</loc></url>\n"
        for name in urls
    )
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}"
        "</urlset>\n"
    )
    return HttpResponse(content, content_type="application/xml; charset=utf-8")
