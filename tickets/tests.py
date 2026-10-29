import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
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
        self.assertEqual(Ticket.objects.get().phone_normalized, "+79991234567")

    def test_admin_can_change_status_and_find_any_phone_format(self):
        self.post()
        user = get_user_model().objects.create_superuser("manager", "manager@example.test", "password")
        admin_client = Client()
        admin_client.force_login(user)
        ticket = Ticket.objects.get()
        url = reverse("admin:tickets_ticket_change", args=[ticket.pk])
        response = admin_client.post(url, {"status": "in_progress", "manager_comment": "Позвонили", "_save": "Сохранить"})
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual((ticket.status, ticket.manager_comment), ("in_progress", "Позвонили"))
        self.assertEqual(ticket.assignee, user)
        for phone in ("+7 (999) 123-45-67", "89991234567", "999 123 45 67"):
            response = admin_client.get(reverse("admin:tickets_ticket_changelist"), {"q": phone})
            self.assertContains(response, ticket.name)

    def test_manager_can_take_ticket_without_superuser_access(self):
        self.post()
        user = get_user_model().objects.create_user("manager", password="password", is_staff=True)
        group = Group.objects.get(name="Менеджеры заявок")
        user.groups.add(group)
        self.assertTrue(user.has_perm("tickets.view_ticket"))
        self.assertTrue(user.has_perm("tickets.change_ticket"))
        self.assertFalse(user.has_perm("tickets.delete_ticket"))
        admin_client = Client()
        admin_client.force_login(user)
        ticket = Ticket.objects.get()
        url = reverse("admin:tickets_ticket_change", args=[ticket.pk])
        self.assertEqual(admin_client.get(url).status_code, 200)
        response = admin_client.post(url, {"status": "in_progress", "manager_comment": "Принял", "_save": "Сохранить"})
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.assignee, user)
        self.assertEqual(ticket.manager_comment, "Принял")

    def test_manager_action_takes_only_unassigned_new_ticket(self):
        self.post()
        user = get_user_model().objects.create_user("manager", password="password", is_staff=True)
        user.groups.add(Group.objects.get(name="Менеджеры заявок"))
        admin_client = Client()
        admin_client.force_login(user)
        ticket = Ticket.objects.get()
        url = reverse("admin:tickets_ticket_changelist")
        response = admin_client.post(url, {
            "action": "take_in_progress", "_selected_action": str(ticket.pk), "index": "0",
        })
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.IN_PROGRESS)
        self.assertEqual(ticket.assignee, user)

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
