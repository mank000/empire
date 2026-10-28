import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from .models import Ticket


class TicketSubmissionTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.url = reverse("create_ticket")
        self.payload = {"name": "Иван", "phone": "+7 (999) 123-45-67", "agreement": True}

    def post(self, payload=None, csrf=True, address="127.0.0.1"):
        headers = {"REMOTE_ADDR": address}
        if csrf:
            self.client.get("/")
            headers["HTTP_X_CSRFTOKEN"] = self.client.cookies["csrftoken"].value
        return self.client.post(
            self.url, data=json.dumps(self.payload if payload is None else payload),
            content_type="application/json", **headers,
        )

    def test_valid_submission_is_saved(self):
        response = self.post()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["ticket_id"], Ticket.objects.get().pk)

    def test_csrf_is_required(self):
        self.assertEqual(self.post(csrf=False).status_code, 403)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_invalid_data_is_rejected(self):
        response = self.post({"name": "A", "phone": "123", "agreement": False})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()["errors"]), {"name", "phone", "agreement"})

    def test_storage_error_does_not_report_success(self):
        with patch("mantage_empire.views.Ticket.objects.create", side_effect=Exception("db unavailable")):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(self.post().status_code, 201)

    def test_repeat_from_same_ip_reaches_django(self):
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(Ticket.objects.count(), 2)

    def test_same_phone_from_another_ip_is_accepted(self):
        self.assertEqual(self.post().status_code, 201)
        response = self.post({**self.payload, "phone": "+79991234567"}, address="127.0.0.2")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Ticket.objects.count(), 2)

    def test_malformed_json_and_get_are_rejected(self):
        self.client.get("/")
        token = self.client.cookies["csrftoken"].value
        response = self.client.post(
            self.url, data="{", content_type="application/json", HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(Ticket.objects.count(), 0)
