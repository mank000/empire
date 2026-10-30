from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings


class RoutingTests(SimpleTestCase):
    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_admin_without_slash_redirects_and_unknown_page_is_404(self):
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/admin/")

        response = self.client.get("/unknown-page/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "404", status_code=404)


class HealthTests(TestCase):
    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_health_reflects_database_availability(self):
        self.assertEqual(self.client.get("/health/").status_code, 200)
        with patch("mantage_empire.views.connection.cursor", side_effect=OSError("database unavailable")):
            with self.assertLogs("mantage_empire.views", level="ERROR"):
                self.assertEqual(self.client.get("/health/").status_code, 503)
