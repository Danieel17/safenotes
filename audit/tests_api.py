from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User

from .models import AuditLog
from .services import log_action


class AuditLogApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin1", password="SafeNotes2026!", role="admin"
        )
        self.editor = User.objects.create_user(
            username="editor1", password="SafeNotes2026!", role="editor"
        )
        self.url = reverse("api-audit-log")

    def _authenticate(self, username, password="SafeNotes2026!"):
        token_url = reverse("api-token-obtain-pair")
        response = self.client.post(
            token_url, {"username": username, "password": password}, format="json"
        )
        access = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_non_admin_forbidden(self):
        self._authenticate("editor1")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_admin_sees_user_created_entry_after_api_creation(self):
        self._authenticate("admin1")
        users_url = reverse("api-user-list-create")
        response = self.client.post(
            users_url,
            {"username": "newlector", "password": "SafeNotes2026!", "role": "lector"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        results = response.data["results"] if "results" in response.data else response.data
        actions = [row["action"] for row in results]
        self.assertIn(AuditLog.ACTION_USER_CREATED, actions)

    def test_filter_by_action(self):
        log_action(actor=self.admin, action=AuditLog.ACTION_LOGIN, target_repr="x")
        log_action(actor=self.admin, action=AuditLog.ACTION_USER_CREATED, target_repr="y")
        self._authenticate("admin1")

        response = self.client.get(self.url, {"action": AuditLog.ACTION_USER_CREATED})
        self.assertEqual(response.status_code, 200)
        results = response.data["results"] if "results" in response.data else response.data
        # At least the two manually-created rows plus the login row from
        # _authenticate() itself; filtering should exclude the login rows.
        for row in results:
            self.assertEqual(row["action"], AuditLog.ACTION_USER_CREATED)

    def test_filter_by_actor(self):
        other = User.objects.create_user(
            username="other", password="SafeNotes2026!", role="editor"
        )
        log_action(actor=other, action=AuditLog.ACTION_LOGIN, target_repr="x")
        self._authenticate("admin1")

        response = self.client.get(self.url, {"actor": "other"})
        self.assertEqual(response.status_code, 200)
        results = response.data["results"] if "results" in response.data else response.data
        for row in results:
            self.assertEqual(row["actor"], "other")
