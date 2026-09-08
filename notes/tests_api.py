from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User

from .models import Category


class CategoryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin1", password="SafeNotes2026!", role="admin"
        )
        self.editor = User.objects.create_user(
            username="editor1", password="SafeNotes2026!", role="editor"
        )
        self.list_url = reverse("category-list")

    def _authenticate(self, username, password="SafeNotes2026!"):
        token_url = reverse("api-token-obtain-pair")
        response = self.client.post(
            token_url, {"username": username, "password": password}, format="json"
        )
        access = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_admin_can_create_category(self):
        self._authenticate("admin1")
        response = self.client.post(self.list_url, {"name": "Finance"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Category.objects.filter(name="Finance").exists())
        category = Category.objects.get(name="Finance")
        self.assertEqual(category.created_by, self.admin)

    def test_non_admin_can_list_categories(self):
        Category.objects.create(name="HR", created_by=self.admin)
        self._authenticate("editor1")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_non_admin_cannot_create_category(self):
        self._authenticate("editor1")
        response = self.client.post(self.list_url, {"name": "Blocked"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Category.objects.filter(name="Blocked").exists())

    def test_non_admin_cannot_update_or_delete_category(self):
        category = Category.objects.create(name="Ops", created_by=self.admin)
        detail_url = reverse("category-detail", args=[category.pk])
        self._authenticate("editor1")

        response = self.client.patch(detail_url, {"name": "Ops2"}, format="json")
        self.assertEqual(response.status_code, 403)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 403)

    def test_categories_require_authentication(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 401)
