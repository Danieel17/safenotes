from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Category


class CategoryManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="cadmin", password="pass12345", role="admin"
        )
        self.editor = User.objects.create_user(
            username="ceditor", password="pass12345", role="editor"
        )

    def test_admin_can_create_category(self):
        self.client.login(username="cadmin", password="pass12345")
        response = self.client.post(reverse("notes:category-create"), {"name": "Work"})
        self.assertEqual(response.status_code, 302)
        category = Category.objects.get(name="Work")
        self.assertEqual(category.created_by, self.admin)

    def test_non_admin_gets_403(self):
        self.client.login(username="ceditor", password="pass12345")
        response = self.client.get(reverse("notes:category-list"))
        self.assertEqual(response.status_code, 403)

    def test_category_list_renders_for_admin(self):
        self.client.login(username="cadmin", password="pass12345")
        response = self.client.get(reverse("notes:category-list"))
        self.assertEqual(response.status_code, 200)
