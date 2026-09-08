from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import path, reverse
from django.views import View

from .mixins import RoleRequiredMixin
from .models import User


class _AdminOnlyView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_role = "admin"

    def get(self, request):
        return HttpResponse("ok")


urlpatterns = [
    path("__test-admin-only__/", _AdminOnlyView.as_view(), name="test-admin-only"),
    path("__test-login__/", lambda request: HttpResponse("login"), name="login"),
]


@override_settings(ROOT_URLCONF="accounts.tests")
class RoleRequiredMixinTests(TestCase):
    """Regression test for RoleRequiredMixin combined with LoginRequiredMixin."""

    def setUp(self):
        self.editor = User.objects.create_user(
            username="editor1", password="pass12345", role="editor"
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role="admin"
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("test-admin-only"))
        self.assertEqual(response.status_code, 302)

    def test_wrong_role_gets_403(self):
        self.client.login(username="editor1", password="pass12345")
        response = self.client.get(reverse("test-admin-only"))
        self.assertEqual(response.status_code, 403)

    def test_correct_role_gets_200(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("test-admin-only"))
        self.assertEqual(response.status_code, 200)


from datetime import timedelta

from django.test import Client
from django.utils import timezone

from audit.models import AuditLog


class LoginLockoutAndAuditTests(TestCase):
    """Ticket 03: lockout behavior and audit logging around login/logout."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="lockme", password="correct-horse-1", role="lector"
        )

    def _fail_login(self, password="wrong-password"):
        return self.client.post(
            reverse("login"), {"username": "lockme", "password": password}
        )

    def test_five_failures_lock_account_and_sixth_correct_attempt_rejected(self):
        for _ in range(5):
            self._fail_login()

        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 5)
        self.assertIsNotNone(self.user.locked_until)
        self.assertGreater(self.user.locked_until, timezone.now())

        response = self._fail_login(password="correct-horse-1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Cuenta bloqueada temporalmente por múltiples intentos fallidos. "
            "Intenta nuevamente más tarde.",
        )

        response = self._fail_login(password="correct-horse-1")
        self.assertContains(
            response,
            "Cuenta bloqueada temporalmente por múltiples intentos fallidos. "
            "Intenta nuevamente más tarde.",
        )

    def test_successful_login_resets_failed_login_count(self):
        self._fail_login()
        self._fail_login()
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 2)

        response = self.client.post(
            reverse("login"), {"username": "lockme", "password": "correct-horse-1"}
        )
        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 0)
        self.assertIsNone(self.user.locked_until)

    def test_successful_login_writes_one_audit_log_row(self):
        self.client.post(
            reverse("login"), {"username": "lockme", "password": "correct-horse-1"}
        )
        logs = AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().actor, self.user)

    def test_failed_login_writes_one_audit_log_row(self):
        self._fail_login()
        logs = AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN_FAILED)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().actor, self.user)

    def test_logout_writes_one_audit_log_row(self):
        self.client.login(username="lockme", password="correct-horse-1")
        self.client.post(reverse("logout"))
        logs = AuditLog.objects.filter(action=AuditLog.ACTION_LOGOUT)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().actor, self.user)

    def test_failed_login_with_nonexistent_username_logs_actor_none(self):
        self.client.post(
            reverse("login"), {"username": "nobody-here", "password": "whatever"}
        )
        logs = AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN_FAILED)
        self.assertEqual(logs.count(), 1)
        self.assertIsNone(logs.first().actor)
        self.assertIn("nobody-here", logs.first().target_repr)

    def test_login_page_renders_extending_base_template(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertTemplateUsed(response, "base.html")

    def test_login_redirect_updates_nav_bar(self):
        response = self.client.post(
            reverse("login"),
            {"username": "lockme", "password": "correct-horse-1"},
            follow=True,
        )
        self.assertContains(response, "lockme")
        self.assertContains(response, "Cerrar sesión")


class AdminUserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin2", password="pass12345", role="admin"
        )
        self.editor = User.objects.create_user(
            username="editor2", password="pass12345", role="editor"
        )
        self.lector = User.objects.create_user(
            username="lector2", password="pass12345", role="lector"
        )

    def test_admin_can_create_editor_and_new_user_can_login(self):
        self.client.login(username="admin2", password="pass12345")
        response = self.client.post(
            reverse("user-create"),
            {"username": "neweditor", "password": "SuperSecret123!", "role": "editor"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="neweditor").exists())

        self.client.logout()
        logged_in = self.client.login(username="neweditor", password="SuperSecret123!")
        self.assertTrue(logged_in)

    def test_deactivating_user_blocks_next_login(self):
        self.client.login(username="admin2", password="pass12345")
        response = self.client.post(reverse("user-toggle-active", args=[self.editor.pk]))
        self.assertEqual(response.status_code, 302)
        self.editor.refresh_from_db()
        self.assertFalse(self.editor.is_active)

        self.client.logout()
        logged_in = self.client.login(username="editor2", password="pass12345")
        self.assertFalse(logged_in)

    def test_non_admin_gets_403_on_admin_urls(self):
        self.client.login(username="editor2", password="pass12345")
        for url in [
            reverse("admin-panel"),
            reverse("user-list"),
            reverse("user-create"),
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username="lector2", password="pass12345")
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, 403)

    def test_audit_log_shows_user_created_row(self):
        self.client.login(username="admin2", password="pass12345")
        self.client.post(
            reverse("user-create"),
            {"username": "audituser", "password": "SuperSecret123!", "role": "lector"},
        )
        response = self.client.get(reverse("audit:log-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "audituser")

    def test_role_change_updates_role_and_logs(self):
        self.client.login(username="admin2", password="pass12345")
        response = self.client.post(
            reverse("user-role-change", args=[self.lector.pk]), {"role": "editor"}
        )
        self.assertEqual(response.status_code, 302)
        self.lector.refresh_from_db()
        self.assertEqual(self.lector.role, "editor")
