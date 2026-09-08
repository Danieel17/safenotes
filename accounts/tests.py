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
