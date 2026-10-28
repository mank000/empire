from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.shortcuts import render
from django.conf import settings
from .views import create_ticket


def not_found(request, exception=None):
    return render(request, "404.html", status=404)

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("admin/", admin.site.urls),
    path("api/tickets/", create_ticket, name="create_ticket"),
    re_path(r"^.*$", not_found, name="not_found"),
]
if settings.DEBUG:
    urlpatterns.insert(2, path("__reload__/", include("django_browser_reload.urls")))

handler404 = not_found
