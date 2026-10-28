from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse
from .views import create_ticket


def not_found(request, exception=None):
    return render(request, "404.html", status=404)


def robots_txt(request):
    return HttpResponse("User-agent: *\nDisallow: /admin/\n", content_type="text/plain; charset=utf-8")

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html", extra_context={"public_site_url": settings.PUBLIC_SITE_URL}), name="home"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("admin/", admin.site.urls),
    path("api/tickets/", create_ticket, name="create_ticket"),
    re_path(r"^.*$", not_found, name="not_found"),
]
if settings.DEBUG:
    urlpatterns.insert(2, path("__reload__/", include("django_browser_reload.urls")))

handler404 = not_found
