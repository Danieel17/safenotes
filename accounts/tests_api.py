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

    def test_lector_can_delete_own_account(self):
        self._authenticate()
        response = self.client.delete(self.profile_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(username="lector1").exists())

    def test_deleting_own_account_logs_user_deleted(self):
        self._authenticate()
        self.client.delete(self.profile_url)
        self.assertTrue(
            AuditLog.objects.filter(
                action="user_deleted", target_repr__icontains="lector1"
            ).exists()
        )

    def test_editor_cannot_delete_own_account_via_profile(self):
        editor = User.objects.create_user(
            username="editor_selfdel", password="SafeNotes2026!", role="editor"
        )
        client = APIClient()
        token_url = reverse("api-token-obtain-pair")
        response = client.post(
            token_url,
            {"username": "editor_selfdel", "password": "SafeNotes2026!"},
            format="json",
        )
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        delete_response = client.delete(self.profile_url)
        self.assertEqual(delete_response.status_code, 403)
        self.assertTrue(User.objects.filter(username="editor_selfdel").exists())


class UserManagementApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin1", password="SafeNotes2026!", role="admin"
        )
        self.editor = User.objects.create_user(
            username="editor1", password="SafeNotes2026!", role="editor"
        )
        self.lector = User.objects.create_user(
            username="lector1", password="SafeNotes2026!", role="lector"
        )
        self.users_url = reverse("api-user-list-create")
        self.token_url = reverse("api-token-obtain-pair")

    def _authenticate(self, username, password="SafeNotes2026!"):
        response = self.client.post(
            self.token_url, {"username": username, "password": password}, format="json"
        )
        access = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return response

    # 1. Admin creates an editor; the new user can immediately obtain a JWT.
    def test_admin_creates_editor_who_can_then_login(self):
        self._authenticate("admin1")
        response = self.client.post(
            self.users_url,
            {"username": "neweditor", "password": "SafeNotes2026!", "role": "editor"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="neweditor", role="editor").exists())

        self.client.credentials()
        login_response = self.client.post(
            self.token_url,
            {"username": "neweditor", "password": "SafeNotes2026!"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("access", login_response.data)

        self.assertEqual(
            AuditLog.objects.filter(
                action=AuditLog.ACTION_USER_CREATED, target_repr="User:neweditor"
            ).count(),
            1,
        )

    def test_create_user_role_restricted_to_editor_lector(self):
        self._authenticate("admin1")
        response = self.client.post(
            self.users_url,
            {"username": "sneaky", "password": "SafeNotes2026!", "role": "admin"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="sneaky").exists())

    # 2. Deactivating a user blocks their next token request.
    def test_deactivating_user_blocks_next_login(self):
        self._authenticate("admin1")
        toggle_url = reverse("api-user-toggle-active", args=[self.editor.pk])
        response = self.client.post(toggle_url)
        self.assertEqual(response.status_code, 200)

        self.editor.refresh_from_db()
        self.assertFalse(self.editor.is_active)

        self.client.credentials()
        login_response = self.client.post(
            self.token_url,
            {"username": "editor1", "password": "SafeNotes2026!"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 401)

    # 3. Non-admins get 403 on admin-only endpoints.
    def test_non_admin_forbidden_on_user_list(self):
        self._authenticate("editor1")
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, 403)

    def test_non_admin_forbidden_on_toggle_and_role(self):
        self._authenticate("lector1")
        toggle_url = reverse("api-user-toggle-active", args=[self.editor.pk])
        response = self.client.post(toggle_url)
        self.assertEqual(response.status_code, 403)

        role_url = reverse("api-user-role", args=[self.editor.pk])
        response = self.client.post(role_url, {"role": "lector"}, format="json")
        self.assertEqual(response.status_code, 403)

    # 6. Admin accounts cannot be toggled or role-changed.
    def test_cannot_toggle_active_admin_target(self):
        other_admin = User.objects.create_user(
            username="admin2", password="SafeNotes2026!", role="admin"
        )
        self._authenticate("admin1")
        toggle_url = reverse("api-user-toggle-active", args=[other_admin.pk])
        response = self.client.post(toggle_url)
        self.assertEqual(response.status_code, 400)
        other_admin.refresh_from_db()
        self.assertTrue(other_admin.is_active)

    def test_cannot_role_change_admin_target(self):
        other_admin = User.objects.create_user(
            username="admin2", password="SafeNotes2026!", role="admin"
        )
        self._authenticate("admin1")
        role_url = reverse("api-user-role", args=[other_admin.pk])
        response = self.client.post(role_url, {"role": "lector"}, format="json")
        self.assertEqual(response.status_code, 400)
        other_admin.refresh_from_db()
        self.assertEqual(other_admin.role, "admin")

    def test_role_change_editor_to_lector(self):
        self._authenticate("admin1")
        role_url = reverse("api-user-role", args=[self.editor.pk])
        response = self.client.post(role_url, {"role": "lector"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.editor.refresh_from_db()
        self.assertEqual(self.editor.role, "lector")
        self.assertEqual(
            AuditLog.objects.filter(action=AuditLog.ACTION_USER_ROLE_CHANGED).count(), 1
        )

    def test_user_list_includes_locked_field(self):
        self._authenticate("admin1")
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, 200)
        results = response.data["results"] if "results" in response.data else response.data
        usernames = {row["username"]: row for row in results}
        self.assertIn("locked", usernames["editor1"])
        self.assertFalse(usernames["editor1"]["locked"])
