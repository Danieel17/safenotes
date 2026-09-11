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

    def test_list_filters_by_category_and_search(self):
        self._authenticate("note_editor1")
        category = Category.objects.create(name="Trabajo", created_by=self.admin)
        other_category = Category.objects.create(name="Personal", created_by=self.admin)

        Note.objects.create(
            owner=self.editor1, title="Reunion equipo", content="x", category=category
        )
        Note.objects.create(
            owner=self.editor1, title="Lista compras", content="y", category=other_category
        )
        Note.objects.create(owner=self.editor1, title="Sin categoria", content="z")

        response = self.client.get(self.list_url, {"category": category.pk})
        self.assertEqual(response.status_code, 200)
        titles = [n["title"] for n in response.data["results"]]
        self.assertEqual(titles, ["Reunion equipo"])

        response = self.client.get(self.list_url, {"search": "lista"})
        titles = [n["title"] for n in response.data["results"]]
        self.assertEqual(titles, ["Lista compras"])

        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data["results"]), 3)

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


from .models import Folder, FolderItem


class SharedNoteAndFolderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.editor = User.objects.create_user(
            username="sn_editor1", password="SafeNotes2026!", role="editor"
        )
        self.lector1 = User.objects.create_user(
            username="sn_lector1", password="SafeNotes2026!", role="lector"
        )
        self.lector2 = User.objects.create_user(
            username="sn_lector2", password="SafeNotes2026!", role="lector"
        )
        self.admin = User.objects.create_user(
            username="sn_admin1", password="SafeNotes2026!", role="admin"
        )
        self.note1 = Note.objects.create(owner=self.editor, title="Note1", content="c1")
        self.note2 = Note.objects.create(owner=self.editor, title="Note2", content="c2")
        self.share1 = Share.objects.create(note=self.note1, shared_with=self.lector1)
        self.share2 = Share.objects.create(note=self.note2, shared_with=self.lector2)

        self.shared_notes_url = reverse("shared-note-list")
        self.folders_url = reverse("folder-list")

    def _authenticate(self, username, password="SafeNotes2026!"):
        token_url = reverse("api-token-obtain-pair")
        response = self.client.post(
            token_url, {"username": username, "password": password}, format="json"
        )
        access = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def _shared_note_detail_url(self, pk):
        return reverse("shared-note-detail", args=[pk])

    def _add_to_folder_url(self, pk):
        return reverse("shared-note-add-to-folder", args=[pk])

    def _folder_detail_url(self, pk):
        return reverse("folder-detail", args=[pk])

    def test_lector_sees_only_own_shares(self):
        self._authenticate("sn_lector1")
        response = self.client.get(self.shared_notes_url)
        self.assertEqual(response.status_code, 200)
        returned_ids = [item["id"] for item in response.data["results"]]
        self.assertIn(self.share1.pk, returned_ids)
        self.assertNotIn(self.share2.pk, returned_ids)

    def test_accessing_another_lectors_share_returns_404(self):
        self._authenticate("sn_lector1")
        response = self.client.get(self._shared_note_detail_url(self.share2.pk))
        self.assertEqual(response.status_code, 404)

    def test_shared_note_detail_logs_one_audit_row_per_request(self):
        self._authenticate("sn_lector1")
        response = self.client.get(self._shared_note_detail_url(self.share1.pk))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self._shared_note_detail_url(self.share1.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            AuditLog.objects.filter(
                action="note_viewed", actor=self.lector1
            ).count(),
            2,
        )

    def test_folder_create_add_delete_preserves_note_and_share(self):
        self._authenticate("sn_lector1")

        response = self.client.post(self.folders_url, {"name": "My Folder"}, format="json")
        self.assertEqual(response.status_code, 201)
        folder_id = response.data["id"]

        response = self.client.post(
            self._add_to_folder_url(self.share1.pk),
            {"folder_id": folder_id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            FolderItem.objects.filter(folder_id=folder_id, share=self.share1).exists()
        )

        response = self.client.delete(self._folder_detail_url(folder_id))
        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            FolderItem.objects.filter(folder_id=folder_id, share=self.share1).exists()
        )
        self.assertTrue(Note.objects.filter(pk=self.note1.pk).exists())
        self.assertTrue(Share.objects.filter(pk=self.share1.pk).exists())

    def test_adding_same_share_to_folder_twice_is_graceful_noop(self):
        self._authenticate("sn_lector1")
        response = self.client.post(self.folders_url, {"name": "Dup Folder"}, format="json")
        folder_id = response.data["id"]

        response = self.client.post(
            self._add_to_folder_url(self.share1.pk),
            {"folder_id": folder_id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            self._add_to_folder_url(self.share1.pk),
            {"folder_id": folder_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            FolderItem.objects.filter(folder_id=folder_id, share=self.share1).count(), 1
        )

    def test_lector_cannot_patch_editors_note_endpoint(self):
        self._authenticate("sn_lector1")
        note_detail_url = reverse("note-detail", args=[self.note1.pk])
        response = self.client.patch(note_detail_url, {"title": "Hacked"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_editor_and_admin_forbidden_from_shared_note_and_folder_endpoints(self):
        self._authenticate("sn_editor1")
        response = self.client.get(self.shared_notes_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(self.folders_url)
        self.assertEqual(response.status_code, 403)

        self._authenticate("sn_admin1")
        response = self.client.get(self.shared_notes_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(self.folders_url)
        self.assertEqual(response.status_code, 403)

    def test_accessing_another_lectors_folder_returns_404(self):
        folder = Folder.objects.create(owner=self.lector2, name="L2 Folder")
        self._authenticate("sn_lector1")
        response = self.client.get(self._folder_detail_url(folder.pk))
        self.assertEqual(response.status_code, 404)
