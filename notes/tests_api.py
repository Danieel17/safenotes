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


from audit.models import AuditLog

from .models import Note, Share


class NoteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.editor1 = User.objects.create_user(
            username="note_editor1", password="SafeNotes2026!", role="editor"
        )
        self.editor2 = User.objects.create_user(
            username="note_editor2", password="SafeNotes2026!", role="editor"
        )
        self.lector = User.objects.create_user(
            username="note_lector1", password="SafeNotes2026!", role="lector"
        )
        self.admin = User.objects.create_user(
            username="note_admin1", password="SafeNotes2026!", role="admin"
        )
        self.list_url = reverse("note-list")

    def _authenticate(self, username, password="SafeNotes2026!"):
        token_url = reverse("api-token-obtain-pair")
        response = self.client.post(
            token_url, {"username": username, "password": password}, format="json"
        )
        access = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def _detail_url(self, pk):
        return reverse("note-detail", args=[pk])

    def _share_url(self, pk):
        return reverse("note-share", args=[pk])

    def _unshare_url(self, pk):
        return reverse("note-unshare", args=[pk])

    def test_editor_can_create_list_update_delete_own_note(self):
        self._authenticate("note_editor1")

        response = self.client.post(
            self.list_url, {"title": "Note A", "content": "secret"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        note_id = response.data["id"]
        self.assertNotIn("owner", response.data)

        # Second editor's own note should not leak into editor1's list.
        other_note = Note.objects.create(
            owner=self.editor2, title="Note B", content="other"
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        returned_ids = [item["id"] for item in response.data["results"]]
        self.assertIn(note_id, returned_ids)
        self.assertNotIn(other_note.pk, returned_ids)

        response = self.client.patch(
            self._detail_url(note_id), {"title": "Note A Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Note A Updated")

        response = self.client.delete(self._detail_url(note_id))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Note.objects.filter(pk=note_id).exists())

    def test_cannot_access_another_editors_note_returns_404(self):
        other_note = Note.objects.create(
            owner=self.editor2, title="Note B", content="other"
        )
        self._authenticate("note_editor1")
        response = self.client.get(self._detail_url(other_note.pk))
        self.assertEqual(response.status_code, 404)

    def test_share_creates_share_and_audit_log(self):
        note = Note.objects.create(owner=self.editor1, title="Shared", content="x")
        self._authenticate("note_editor1")

        response = self.client.post(
            self._share_url(note.pk), {"shared_with": self.lector.pk}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Share.objects.filter(note=note, shared_with=self.lector).count(), 1)
        self.assertEqual(
            AuditLog.objects.filter(action="note_shared", actor=self.editor1).count(), 1
        )

    def test_duplicate_share_is_graceful_noop(self):
        note = Note.objects.create(owner=self.editor1, title="Shared", content="x")
        Share.objects.create(note=note, shared_with=self.lector)
        self._authenticate("note_editor1")

        response = self.client.post(
            self._share_url(note.pk), {"shared_with": self.lector.pk}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Share.objects.filter(note=note, shared_with=self.lector).count(), 1)

    def test_share_with_non_lector_rejected(self):
        note = Note.objects.create(owner=self.editor1, title="Shared", content="x")
        self._authenticate("note_editor1")

        response = self.client.post(
            self._share_url(note.pk), {"shared_with": self.editor2.pk}, format="json"
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            self._share_url(note.pk), {"shared_with": self.admin.pk}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_lector_and_admin_forbidden_from_note_endpoints(self):
        note = Note.objects.create(owner=self.editor1, title="Note", content="x")

        self._authenticate("note_lector1")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

        self._authenticate("note_admin1")
        response = self.client.get(self._detail_url(note.pk))
        self.assertEqual(response.status_code, 403)

    def test_unshare_removes_share_row(self):
        note = Note.objects.create(owner=self.editor1, title="Shared", content="x")
        Share.objects.create(note=note, shared_with=self.lector)
        self._authenticate("note_editor1")

        response = self.client.post(
            self._unshare_url(note.pk), {"shared_with": self.lector.pk}, format="json"
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Share.objects.filter(note=note, shared_with=self.lector).exists())
