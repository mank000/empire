from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import Case, FAQ, SiteSettings


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

    def test_repeated_home_request_uses_cached_content(self):
        self.client.get(reverse("home"))
        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse("home"))
        self.assertFalse([query for query in queries if '"site_content_' in query["sql"]])
