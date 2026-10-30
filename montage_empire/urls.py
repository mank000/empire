from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import health
from site_content.views import home, not_found, privacy_policy, requisites, robots_txt, sitemap_xml
from tickets.views import create_ticket

urlpatterns = [
    path("health/", health, name="health"),
    path("", home, name="home"),
    path("privacy-policy/", privacy_policy, name="privacy_policy"),
    path("requisites/", requisites, name="requisites"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("admin/", admin.site.urls),
    path("api/tickets/", create_ticket, name="create_ticket"),
]
if settings.DEBUG:
    urlpatterns.insert(2, path("__reload__/", include("django_browser_reload.urls")))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = not_found
