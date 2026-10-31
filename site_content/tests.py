from html.parser import HTMLParser
from xml.etree import ElementTree

from django.core.cache import cache
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import Case, FAQ, SiteSettings


class PublicRouteTests(SimpleTestCase):
    @override_settings(PUBLIC_SITE_URL="https://example.test", SECURE_SSL_REDIRECT=False)
    def test_robots_points_to_public_sitemap_and_blocks_admin(self):
        response = self.client.get(reverse("robots_txt"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/plain"))
        self.assertEqual(
            response.content.decode(),
            "User-agent: *\nDisallow: /admin/\nSitemap: https://example.test/sitemap.xml\n",
        )

    @override_settings(PUBLIC_SITE_URL="https://example.test", SECURE_SSL_REDIRECT=False)
    def test_sitemap_is_valid_xml_with_public_urls(self):
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/xml"))
        root = ElementTree.fromstring(response.content)
        namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        self.assertEqual(root.tag, f"{namespace}urlset")
        self.assertEqual(
            [element.text for element in root.findall(f"{namespace}url/{namespace}loc")],
            ["https://example.test/", "https://example.test/privacy-policy/", "https://example.test/requisites/"],
        )

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_unknown_page_uses_custom_404_without_indexing(self):
        response = self.client.get("/missing/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Страница не найдена", status_code=404)
        self.assertContains(response, '<meta name="robots" content="noindex">', status_code=404)


class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.append(dict(attrs))


class HomeContentTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_seeded_content_is_visible_and_settings_update_immediately(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "+7 (904) 626 06 94")
        self.assertContains(response, "Бизнес-центр Сбербанка")
        self.assertContains(response, "ВЫЕЗД ИНЖЕНЕРА")
        self.assertContains(response, "Сбербанк")

        settings = SiteSettings.objects.get(pk=1)
        settings.phone = "+7 (999) 111-22-33"
        settings.save()
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "+7 (904) 626 06 94")
        self.assertContains(response, "tel:+79991112233")
        self.assertContains(response, "+7 (999) 111-22-33", count=5)

    def test_case_and_faq_changes_invalidate_cached_home(self):
        self.client.get(reverse("home"))
        Case.objects.create(
            title="Новый объект", description="Описание", tags="СКУД", status_text="Сдан",
            metric_1_value="1", metric_1_label="Камера",
            metric_2_value="2", metric_2_label="Дня",
            metric_3_value="3", metric_3_label="Входа",
            initial_image="img/administrativeobjects.webp", order=4,
        )
        faq = FAQ.objects.first()
        faq.is_visible = False
        faq.save()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Новый объект")
        self.assertNotContains(response, faq.question)

    def test_site_settings_is_singleton(self):
        settings = SiteSettings.objects.get(pk=1)
        settings.pk = None
        settings.save()
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_policy_requisites_links_and_sitemap(self):
        settings = SiteSettings.objects.get(pk=1)
        settings.privacy_policy = "Текст политики клиента"
        settings.save()
        self.assertContains(self.client.get(reverse("privacy_policy")), "Текст политики клиента")
        self.assertContains(self.client.get(reverse("requisites")), settings.inn)
        home = self.client.get(reverse("home"))
        self.assertContains(home, 'href="/privacy-policy/"', count=3)
        self.assertContains(home, 'href="/requisites/"')
        sitemap = self.client.get(reverse("sitemap"))
        self.assertContains(sitemap, "/privacy-policy/")

    def test_repeated_home_request_uses_cached_content(self):
        self.client.get(reverse("home"))
        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse("home"))
        self.assertFalse([query for query in queries if '"site_content_' in query["sql"]])

    def test_ticket_forms_do_not_submit_without_javascript(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'method="post" action="/api/tickets/"', count=2)
        self.assertContains(response, '<button type="submit" class="make-ticket-submit" disabled>', count=2)
        self.assertContains(response, 'id="make-ticket-phone"')
        self.assertContains(response, 'id="request-modal-phone"')

    def test_footer_social_links_and_image_sizes(self):
        settings = SiteSettings.objects.get(pk=1)
        settings.telegram_url = "https://t.me/example"
        settings.whatsapp_url = "https://wa.me/79991234567"
        settings.save()
        response = self.client.get(reverse("home"))
        html = response.content.decode()
        self.assertIn('<footer class="footer"', html)
        self.assertLess(html.index("</main>"), html.index('<footer class="footer"'))
        self.assertContains(response, 'href="https://t.me/example"', count=3)
        self.assertContains(response, 'href="https://wa.me/79991234567"', count=3)
        self.assertNotIn('href="#"', html)
        images = ImageParser()
        images.feed(html)
        self.assertTrue(images.images)
        self.assertTrue(all(image.get("width") and image.get("height") for image in images.images))
