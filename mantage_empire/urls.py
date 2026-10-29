from django.contrib import admin
from django.urls import path, include, re_path, reverse
from django.views.generic import TemplateView
from django.shortcuts import render
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from xml.sax.saxutils import escape
from .views import create_ticket, home, privacy_policy, requisites


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

urlpatterns = [
    path("", home, name="home"),
    path("privacy-policy/", privacy_policy, name="privacy_policy"),
    path("requisites/", requisites, name="requisites"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("admin/", admin.site.urls),
    path("api/tickets/", create_ticket, name="create_ticket"),
    re_path(r"^.*$", not_found, name="not_found"),
]
if settings.DEBUG:
    urlpatterns.insert(2, path("__reload__/", include("django_browser_reload.urls")))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = not_found
