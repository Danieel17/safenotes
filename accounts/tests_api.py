import base64
import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditLog

from .models import User


def decode_jwt_payload(token):
    payload_segment = token.split(".")[1]
    padding = "=" * (-len(payload_segment) % 4)
    decoded = base64.urlsafe_b64decode(payload_segment + padding)
    return json.loads(decoded)


class AuthLockoutApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="editor1", password="SafeNotes2026!", role="editor"
        )
        self.token_url = reverse("api-token-obtain-pair")
        self.refresh_url = reverse("api-token-refresh")
        self.logout_url = reverse("api-logout")
        self.profile_url = reverse("api-profile")

    def test_successful_login_returns_tokens_with_role_claim(self):
        response = self.client.post(
            self.token_url,
            {"username": "editor1", "password": "SafeNotes2026!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        payload = decode_jwt_payload(response.data["access"])
        self.assertEqual(payload["role"], "editor")

    def test_five_failed_logins_lock_account_then_reject_correct_password(self):
        for _ in range(5):
            response = self.client.post(
                self.token_url,
                {"username": "editor1", "password": "wrong-password"},
                format="json",
            )
            self.assertEqual(response.status_code, 401)

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.locked_until)
        self.assertGreater(self.user.locked_until, timezone.now())

        # 6th attempt, correct password, still rejected due to lockout.
        response = self.client.post(
            self.token_url,
            {"username": "editor1", "password": "SafeNotes2026!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("bloqueada", str(response.data))

    def test_successful_login_after_failures_resets_counter(self):
        for _ in range(3):
            self.client.post(
                self.token_url,
                {"username": "editor1", "password": "wrong-password"},
                format="json",
            )
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 3)

        response = self.client.post(
            self.token_url,
            {"username": "editor1", "password": "SafeNotes2026!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 0)
        self.assertIsNone(self.user.locked_until)

    def test_audit_log_rows_for_login_failure_success_and_logout(self):
        self.client.post(
            self.token_url,
            {"username": "editor1", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(
            AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN_FAILED).count(), 1
        )

        response = self.client.post(
            self.token_url,
            {"username": "editor1", "password": "SafeNotes2026!"},
            format="json",
        )
        self.assertEqual(
            AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN).count(), 1
        )

        access = response.data["access"]
        refresh = response.data["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout_response = self.client.post(
            self.logout_url, {"refresh": refresh}, format="json"
        )
        self.assertIn(logout_response.status_code, (200, 205))
        self.assertEqual(
            AuditLog.objects.filter(action=AuditLog.ACTION_LOGOUT).count(), 1
        )

    def test_login_failure_for_nonexistent_username_logs_actor_none(self):
        response = self.client.post(
            self.token_url,
            {"username": "doesnotexist", "password": "whatever"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

        log = AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN_FAILED).latest(
            "timestamp"
        )
        self.assertIsNone(log.actor)

    def test_logout_blacklists_refresh_token(self):
        response = self.client.post(
            self.token_url,
            {"username": "editor1", "password": "SafeNotes2026!"},
            format="json",
        )
        access = response.data["access"]
        refresh = response.data["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout_response = self.client.post(
            self.logout_url, {"refresh": refresh}, format="json"
        )
        self.assertIn(logout_response.status_code, (200, 205))

        self.client.credentials()
        refresh_response = self.client.post(
            self.refresh_url, {"refresh": refresh}, format="json"
        )
        self.assertEqual(refresh_response.status_code, 401)


class ProfileApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="lector1",
            password="SafeNotes2026!",
            role="lector",
            email="lector1@example.com",
        )
        self.profile_url = reverse("api-profile")

    def _authenticate(self):
        token_url = reverse("api-token-obtain-pair")
        response = self.client.post(
            token_url,
            {"username": "lector1", "password": "SafeNotes2026!"},
            format="json",
        )
        access = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_get_profile_returns_own_data(self):
        self._authenticate()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "lector1")
        self.assertEqual(response.data["email"], "lector1@example.com")
        self.assertEqual(response.data["role"], "lector")

    def test_patch_profile_updates_email(self):
        self._authenticate()
        response = self.client.patch(
            self.profile_url, {"email": "new-email@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new-email@example.com")

    def test_profile_requires_authentication(self):
        get_response = self.client.get(self.profile_url)
        self.assertEqual(get_response.status_code, 401)

        patch_response = self.client.patch(
            self.profile_url, {"email": "x@example.com"}, format="json"
        )
        self.assertEqual(patch_response.status_code, 401)
