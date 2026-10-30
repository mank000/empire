import json
import os
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import NotificationChannelState, NotificationDelivery, NotificationSettings, Ticket
from .secrets import encrypt_token
from .tasks import dispatch_pending_notifications, send_notification
from .management.commands.dispatch_notifications import Command


class TicketSubmissionTests(TestCase):
    def setUp(self):
        key_patch = patch.dict(os.environ, {"NOTIFICATION_ENCRYPTION_KEY": Fernet.generate_key().decode()})
        key_patch.start()
        self.addCleanup(key_patch.stop)
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
        self.assertIsNotNone(Ticket.objects.get().consent_at)
        self.assertEqual(Ticket.objects.get().phone, "+79991234567")
        self.assertEqual(Ticket.objects.get().phone_normalized, "+79991234567")

    def test_programmatic_ticket_save_normalizes_phone_for_admin(self):
        ticket = Ticket.objects.create(name="Анна", phone="8 (999) 123-45-67")
        self.assertEqual(ticket.phone, "+79991234567")
        self.assertEqual(ticket.phone_normalized, ticket.phone)

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

    def test_api_failure_retries_without_delaying_ticket_response(self):
        config = NotificationSettings.objects.get(pk=1)
        config.telegram_enabled = True
        config.telegram_chat_id = "123"
        config.telegram_token_encrypted = encrypt_token("test-token")
        config.save()
        with patch("tickets.tasks.send_telegram") as sender:
            response = self.post()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Ticket.objects.count(), 1)
        sender.assert_not_called()
        delivery = NotificationDelivery.objects.get()
        self.assertEqual(delivery.status, NotificationDelivery.Status.PENDING)

        with patch("tickets.tasks.send_notification.apply_async") as publish:
            dispatch_pending_notifications.run()
        publish.assert_called_once()
        with patch("tickets.tasks.send_telegram", side_effect=TimeoutError):
            with self.assertLogs("tickets.tasks", level="ERROR"):
                send_notification.run(delivery.pk)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, NotificationDelivery.Status.PENDING)
        self.assertEqual(delivery.attempts, 1)
        self.assertEqual(Ticket.objects.count(), 1)

        delivery.next_attempt_at = timezone.now()
        delivery.save(update_fields=["next_attempt_at"])
        NotificationChannelState.objects.filter(channel=delivery.channel).update(next_allowed_at=timezone.now())
        with patch("tickets.tasks.send_notification.apply_async"):
            dispatch_pending_notifications.run()
        with patch("tickets.tasks.send_telegram") as sender:
            send_notification.run(delivery.pk)
        sender.assert_called_once()
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, NotificationDelivery.Status.SENT)

    def test_max_channel_and_disable_switch(self):
        config = NotificationSettings.objects.get(pk=1)
        config.max_enabled = True
        config.max_chat_id = "456"
        config.max_token_encrypted = encrypt_token("max-test-token")
        config.save()
        self.assertEqual(self.post().status_code, 201)
        delivery = NotificationDelivery.objects.get()
        with patch("tickets.tasks.send_notification.apply_async"):
            dispatch_pending_notifications.run()
        with patch("tickets.tasks.send_max") as sender:
            send_notification.run(delivery.pk)
        sender.assert_called_once()
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, NotificationDelivery.Status.SENT)

        self.assertEqual(self.post().status_code, 201)
        second = NotificationDelivery.objects.latest("pk")
        config.max_enabled = False
        config.save()
        NotificationChannelState.objects.filter(channel=second.channel).update(next_allowed_at=timezone.now())
        with patch("tickets.tasks.send_notification.apply_async"):
            dispatch_pending_notifications.run()
        with patch("tickets.tasks.send_max") as sender:
            send_notification.run(second.pk)
        sender.assert_not_called()
        second.refresh_from_db()
        self.assertEqual(second.status, NotificationDelivery.Status.SKIPPED)

    def test_broker_failure_keeps_notification_pending(self):
        config = NotificationSettings.objects.get(pk=1)
        config.telegram_enabled = True
        config.save()
        self.assertEqual(self.post().status_code, 201)
        with patch("tickets.tasks.send_notification.apply_async", side_effect=ConnectionError):
            with self.assertLogs("tickets.tasks", level="ERROR"):
                dispatch_pending_notifications.run()
        delivery = NotificationDelivery.objects.get()
        self.assertEqual(delivery.status, NotificationDelivery.Status.PENDING)
        self.assertEqual(Ticket.objects.count(), 1)

    def test_dispatch_queues_only_one_per_channel(self):
        config = NotificationSettings.objects.get(pk=1)
        config.telegram_enabled = True
        config.save()
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 201)
        with patch("tickets.tasks.send_notification.apply_async") as publish:
            dispatch_pending_notifications.run()
            dispatch_pending_notifications.run()
        publish.assert_called_once()
        self.assertEqual(NotificationDelivery.objects.filter(status=NotificationDelivery.Status.QUEUED).count(), 1)
        self.assertEqual(NotificationDelivery.objects.filter(status=NotificationDelivery.Status.PENDING).count(), 1)

    def test_global_channel_limit_defers_without_an_api_call(self):
        config = NotificationSettings.objects.get(pk=1)
        config.telegram_enabled = True
        config.telegram_chat_id = "123"
        config.telegram_token_encrypted = encrypt_token("test-token")
        config.save()
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 201)
        first, second = NotificationDelivery.objects.order_by("pk")
        with patch("tickets.tasks.send_notification.apply_async"):
            dispatch_pending_notifications.run()
        with patch("tickets.tasks.send_telegram") as sender:
            send_notification.run(first.pk)
            second.status = NotificationDelivery.Status.QUEUED
            second.lease_until = timezone.now() + timedelta(minutes=2)
            second.save(update_fields=["status", "lease_until"])
            send_notification.run(second.pk)
        sender.assert_called_once()
        second.refresh_from_db()
        self.assertEqual(second.status, NotificationDelivery.Status.PENDING)
        self.assertEqual(second.attempts, 0)
        self.assertGreater(second.next_attempt_at, timezone.now())

    def test_old_backlog_is_sent_as_one_summary(self):
        config = NotificationSettings.objects.get(pk=1)
        config.telegram_enabled = True
        config.telegram_chat_id = "123"
        config.telegram_token_encrypted = encrypt_token("test-token")
        config.save()
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 201)
        NotificationDelivery.objects.update(created_at=timezone.now() - timedelta(hours=2))
        with patch("tickets.tasks.send_notification.apply_async") as publish:
            dispatch_pending_notifications.run()
        publish.assert_called_once()
        delivery = NotificationDelivery.objects.filter(status=NotificationDelivery.Status.QUEUED).get()
        with patch("tickets.tasks.send_telegram") as sender:
            send_notification.run(delivery.pk)
        self.assertIn("2 заявок", sender.call_args.args[2])
        self.assertEqual(NotificationDelivery.objects.filter(status=NotificationDelivery.Status.SUMMARIZED).count(), 2)

    def test_dispatcher_does_not_publish_without_worker(self):
        with patch("tickets.management.commands.dispatch_notifications.app.control.ping", return_value=[]):
            with patch("tickets.management.commands.dispatch_notifications.dispatch_pending_notifications") as dispatch:
                self.assertFalse(Command().dispatch_once())
        dispatch.run.assert_not_called()

    def test_email_channel_uses_same_outbox(self):
        config = NotificationSettings.objects.get(pk=1)
        config.email_enabled = True
        config.email_recipient = "manager@example.test"
        config.save()
        self.assertEqual(self.post().status_code, 201)
        delivery = NotificationDelivery.objects.get()
        self.assertEqual(delivery.channel, NotificationDelivery.Channel.EMAIL)
        with patch("tickets.tasks.send_notification.apply_async"):
            dispatch_pending_notifications.run()
        with patch("tickets.tasks.send_email") as sender:
            send_notification.run(delivery.pk)
        sender.assert_called_once()
        self.assertEqual(sender.call_args.args[0], "manager@example.test")
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, NotificationDelivery.Status.SENT)

    @override_settings(MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}})
    def test_email_message_contains_ticket(self):
        from .notifications import send_email

        send_email("manager@example.test", "Новая заявка #42")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["manager@example.test"])
        self.assertIn("#42", mail.outbox[0].body)

    def test_dev_token_works_without_encryption_key(self):
        with patch.dict(os.environ, {"NOTIFICATION_ENCRYPTION_KEY": ""}):
            with override_settings(DEBUG=True):
                encrypted = encrypt_token("local-token")
                self.assertEqual(encrypted, "dev-plaintext:local-token")
                config = NotificationSettings.objects.get(pk=1)
                config.telegram_token_encrypted = encrypted
                self.assertEqual(config.token_for(NotificationDelivery.Channel.TELEGRAM), "local-token")
            with override_settings(DEBUG=False):
                with self.assertRaisesMessage(Exception, "dev нельзя использовать в production"):
                    config.token_for(NotificationDelivery.Channel.TELEGRAM)

    def test_production_token_is_encrypted(self):
        with override_settings(DEBUG=False):
            encrypted = encrypt_token("production-token")
            self.assertNotIn("production-token", encrypted)
            config = NotificationSettings.objects.get(pk=1)
            config.telegram_token_encrypted = encrypted
            self.assertEqual(config.token_for(NotificationDelivery.Channel.TELEGRAM), "production-token")

    def test_three_failures_pause_channel(self):
        config = NotificationSettings.objects.get(pk=1)
        config.telegram_enabled = True
        config.telegram_chat_id = "123"
        config.telegram_token_encrypted = encrypt_token("test-token")
        config.save()
        self.assertEqual(self.post().status_code, 201)
        delivery = NotificationDelivery.objects.get()
        for _ in range(3):
            NotificationDelivery.objects.filter(pk=delivery.pk).update(
                status=NotificationDelivery.Status.QUEUED, lease_until=timezone.now() + timedelta(minutes=2),
            )
            NotificationChannelState.objects.filter(channel=delivery.channel).update(next_allowed_at=timezone.now())
            with patch("tickets.tasks.send_telegram", side_effect=TimeoutError):
                with self.assertLogs("tickets.tasks", level="ERROR"):
                    send_notification.run(delivery.pk)
        state = NotificationChannelState.objects.get(channel=delivery.channel)
        self.assertEqual(state.consecutive_failures, 3)
        self.assertGreater(state.paused_until, timezone.now())
        with patch("tickets.tasks.send_notification.apply_async") as publish:
            dispatch_pending_notifications.run()
        publish.assert_not_called()

    def test_maxo_client_receives_chat_and_text(self):
        from .notifications import send_max

        with patch("tickets.notifications.Bot") as bot_class:
            bot = bot_class.return_value
            bot.__aenter__ = AsyncMock(return_value=bot)
            bot.__aexit__ = AsyncMock()
            bot.send_message = AsyncMock()
            send_max("test-token", "456", "Новая заявка")
        bot_class.assert_called_once_with("test-token", warming_up=False)
        bot.send_message.assert_awaited_once_with(chat_id=456, text="Новая заявка")

    def test_admin_can_replace_and_disable_encrypted_tokens(self):
        user = get_user_model().objects.create_superuser("owner", "owner@example.test", "password")
        admin_client = Client()
        admin_client.force_login(user)
        url = reverse("admin:tickets_notificationsettings_change", args=[1])
        response = admin_client.post(url, {
            "telegram_enabled": "on", "telegram_chat_id": "123",
            "telegram_token": "secret-in-admin", "max_chat_id": "",
            "_save": "Сохранить",
        })
        self.assertEqual(response.status_code, 302)
        config = NotificationSettings.objects.get(pk=1)
        self.assertEqual(config.token_for(NotificationDelivery.Channel.TELEGRAM), "secret-in-admin")

        staff = get_user_model().objects.create_user("staff", password="password", is_staff=True)
        staff_client = Client()
        staff_client.force_login(staff)
        self.assertEqual(staff_client.get(url).status_code, 403)
        self.assertNotIn("secret-in-admin", config.telegram_token_encrypted)
        self.assertNotContains(admin_client.get(url), "secret-in-admin")
        response = admin_client.post(url, {"telegram_chat_id": "123", "max_chat_id": "", "_save": "Сохранить"})
        self.assertEqual(response.status_code, 302)
        config.refresh_from_db()
        self.assertFalse(config.telegram_enabled)
        self.assertEqual(config.token_for(NotificationDelivery.Channel.TELEGRAM), "secret-in-admin")

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
