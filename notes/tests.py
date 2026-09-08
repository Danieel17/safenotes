from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from audit.models import AuditLog

from .models import Category, Folder, FolderItem, Note, Share


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


from django.db import IntegrityError, connection, transaction

from .models import Folder, FolderItem, Note, Share


class NoteEncryptionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="noteowner", password="pass12345", role="editor"
        )

    def test_content_round_trips_through_fresh_fetch(self):
        note = Note.objects.create(
            owner=self.owner, title="t", content="texto secreto de prueba"
        )
        fetched = Note.objects.get(pk=note.pk)
        self.assertEqual(fetched.content, "texto secreto de prueba")

    def test_raw_db_storage_does_not_contain_plaintext(self):
        note = Note.objects.create(
            owner=self.owner, title="t", content="texto secreto de prueba"
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT content FROM notes_note WHERE id = %s", [note.pk]
            )
            raw_value = cursor.fetchone()[0]
        self.assertNotEqual(raw_value, "texto secreto de prueba")
        self.assertNotIn("texto secreto de prueba", raw_value)


class ShareFolderTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="shareowner", password="pass12345", role="editor"
        )
        self.other = User.objects.create_user(
            username="otheruser", password="pass12345", role="lector"
        )
        self.note = Note.objects.create(
            owner=self.owner, title="t", content="contenido"
        )

    def test_create_share_folder_and_folderitem(self):
        share = Share.objects.create(note=self.note, shared_with=self.other)
        folder = Folder.objects.create(owner=self.other, name="Mis notas")
        item = FolderItem.objects.create(folder=folder, share=share)
        self.assertEqual(item.folder, folder)
        self.assertEqual(item.share, share)

    def test_duplicate_share_raises_integrity_error(self):
        Share.objects.create(note=self.note, shared_with=self.other)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Share.objects.create(note=self.note, shared_with=self.other)

    def test_duplicate_folderitem_raises_integrity_error(self):
        share = Share.objects.create(note=self.note, shared_with=self.other)
        folder = Folder.objects.create(owner=self.other, name="Mis notas")
        FolderItem.objects.create(folder=folder, share=share)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FolderItem.objects.create(folder=folder, share=share)


from audit.models import AuditLog


class EditorNoteCrudTests(TestCase):
    def setUp(self):
        self.editor = User.objects.create_user(
            username="edcrud1", password="pass12345", role="editor"
        )
        self.other_editor = User.objects.create_user(
            username="edcrud2", password="pass12345", role="editor"
        )
        self.lector = User.objects.create_user(
            username="lectorcrud", password="pass12345", role="lector"
        )
        self.admin = User.objects.create_user(
            username="admincrud", password="pass12345", role="admin"
        )

    def test_editor_can_create_view_edit_delete_own_note(self):
        self.client.login(username="edcrud1", password="pass12345")

        response = self.client.post(
            reverse("notes:note-create"),
            {"title": "My note", "content": "secret content", "category": ""},
        )
        self.assertEqual(response.status_code, 302)
        note = Note.objects.get(title="My note", owner=self.editor)

        response = self.client.get(reverse("notes:note-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My note")

        response = self.client.post(
            reverse("notes:note-update", args=[note.pk]),
            {"title": "Updated note", "content": "secret content", "category": ""},
        )
        self.assertEqual(response.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.title, "Updated note")

        response = self.client.post(reverse("notes:note-delete", args=[note.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())

    def test_editor_cannot_reach_other_editors_note(self):
        other_note = Note.objects.create(
            owner=self.other_editor, title="Not yours", content="x"
        )
        self.client.login(username="edcrud1", password="pass12345")

        response = self.client.get(reverse("notes:note-detail", args=[other_note.pk]))
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse("notes:note-update", args=[other_note.pk]))
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse("notes:note-delete", args=[other_note.pk]))
        self.assertEqual(response.status_code, 404)

    def test_lector_and_admin_get_403_on_editor_note_urls(self):
        note = Note.objects.create(owner=self.editor, title="t", content="x")

        self.client.login(username="lectorcrud", password="pass12345")
        response = self.client.get(reverse("notes:note-list"))
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username="admincrud", password="pass12345")
        response = self.client.get(reverse("notes:note-list"))
        self.assertEqual(response.status_code, 403)


class EditorNoteSharingTests(TestCase):
    def setUp(self):
        self.editor = User.objects.create_user(
            username="edshare1", password="pass12345", role="editor"
        )
        self.lector = User.objects.create_user(
            username="lectorshare", password="pass12345", role="lector"
        )
        self.note = Note.objects.create(
            owner=self.editor, title="Shared note", content="content"
        )

    def test_sharing_creates_share_and_audit_row(self):
        self.client.login(username="edshare1", password="pass12345")
        response = self.client.post(
            reverse("notes:note-share", args=[self.note.pk]),
            {"shared_with": self.lector.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Share.objects.filter(note=self.note, shared_with=self.lector).count(), 1)
        self.assertEqual(
            AuditLog.objects.filter(action=AuditLog.ACTION_NOTE_SHARED).count(), 1
        )

    def test_sharing_same_lector_twice_does_not_duplicate_or_crash(self):
        self.client.login(username="edshare1", password="pass12345")
        self.client.post(
            reverse("notes:note-share", args=[self.note.pk]),
            {"shared_with": self.lector.pk},
        )
        response = self.client.post(
            reverse("notes:note-share", args=[self.note.pk]),
            {"shared_with": self.lector.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Share.objects.filter(note=self.note, shared_with=self.lector).count(), 1)
        self.assertEqual(
            AuditLog.objects.filter(action=AuditLog.ACTION_NOTE_SHARED).count(), 1
        )

    def test_delete_note_cascades_to_shares(self):
        Share.objects.create(note=self.note, shared_with=self.lector)
        self.assertEqual(Share.objects.filter(note=self.note).count(), 1)
        note_pk = self.note.pk

        self.client.login(username="edshare1", password="pass12345")
        response = self.client.post(reverse("notes:note-delete", args=[self.note.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Note.objects.filter(pk=note_pk).exists())
        self.assertFalse(Share.objects.filter(note_id=note_pk).exists())


class LectorSharedNoteVisibilityTests(TestCase):
    def setUp(self):
        self.editor = User.objects.create_user(
            username="lsv_editor", password="pass12345", role="editor"
        )
        self.lector_a = User.objects.create_user(
            username="lsv_lectora", password="pass12345", role="lector"
        )
        self.lector_b = User.objects.create_user(
            username="lsv_lectorb", password="pass12345", role="lector"
        )
        self.note = Note.objects.create(
            owner=self.editor, title="Private-ish", content="secret content"
        )
        self.share = Share.objects.create(note=self.note, shared_with=self.lector_a)

    def test_lector_sees_only_own_shared_notes(self):
        self.client.login(username="lsv_lectora", password="pass12345")
        response = self.client.get(reverse("notes:shared-note-list"))
        self.assertContains(response, "Private-ish")

        self.client.logout()
        self.client.login(username="lsv_lectorb", password="pass12345")
        response = self.client.get(reverse("notes:shared-note-list"))
        self.assertNotContains(response, "Private-ish")

    def test_lector_cannot_view_note_not_shared_with_them(self):
        self.client.login(username="lsv_lectorb", password="pass12345")
        response = self.client.get(
            reverse("notes:shared-note-detail", args=[self.share.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_viewing_shared_note_logs_note_viewed_once(self):
        self.client.login(username="lsv_lectora", password="pass12345")
        response = self.client.get(
            reverse("notes:shared-note-detail", args=[self.share.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "secret content")
        self.assertEqual(
            AuditLog.objects.filter(
                action=AuditLog.ACTION_NOTE_VIEWED,
                target_repr=f"Note:{self.note.pk}",
            ).count(),
            1,
        )


class LectorFolderCrudTests(TestCase):
    def setUp(self):
        self.editor = User.objects.create_user(
            username="lfc_editor", password="pass12345", role="editor"
        )
        self.lector = User.objects.create_user(
            username="lfc_lector", password="pass12345", role="lector"
        )
        self.other_lector = User.objects.create_user(
            username="lfc_other", password="pass12345", role="lector"
        )
        self.note = Note.objects.create(
            owner=self.editor, title="Folder note", content="content"
        )
        self.share = Share.objects.create(note=self.note, shared_with=self.lector)

    def test_full_folder_lifecycle(self):
        self.client.login(username="lfc_lector", password="pass12345")

        # Create
        response = self.client.post(
            reverse("notes:folder-create"), {"name": "My folder"}
        )
        self.assertEqual(response.status_code, 302)
        folder = Folder.objects.get(name="My folder", owner=self.lector)

        # Add shared note to folder
        response = self.client.post(
            reverse("notes:shared-note-add-to-folder", args=[self.share.pk]),
            {"folder": folder.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            FolderItem.objects.filter(folder=folder, share=self.share).count(), 1
        )

        # Adding the same note twice does not crash or duplicate
        response = self.client.post(
            reverse("notes:shared-note-add-to-folder", args=[self.share.pk]),
            {"folder": folder.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            FolderItem.objects.filter(folder=folder, share=self.share).count(), 1
        )

        # Rename
        response = self.client.post(
            reverse("notes:folder-update", args=[folder.pk]), {"name": "Renamed"}
        )
        self.assertEqual(response.status_code, 302)
        folder.refresh_from_db()
        self.assertEqual(folder.name, "Renamed")

        # Delete: removes FolderItem, keeps Note and Share
        note_pk = self.note.pk
        share_pk = self.share.pk
        response = self.client.post(reverse("notes:folder-delete", args=[folder.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Folder.objects.filter(pk=folder.pk).exists())
        self.assertFalse(FolderItem.objects.filter(folder_id=folder.pk).exists())
        self.assertTrue(Note.objects.filter(pk=note_pk).exists())
        self.assertTrue(Share.objects.filter(pk=share_pk).exists())

    def test_cannot_add_another_lectors_share_via_own_folder(self):
        self.client.login(username="lfc_other", password="pass12345")
        response = self.client.post(
            reverse("notes:folder-create"), {"name": "Other folder"}
        )
        self.assertEqual(response.status_code, 302)
        other_folder = Folder.objects.get(name="Other folder", owner=self.other_lector)

        # other_lector tries to add lfc_lector's share into their own folder
        response = self.client.post(
            reverse("notes:shared-note-add-to-folder", args=[self.share.pk]),
            {"folder": other_folder.pk},
        )
        # The share lookup itself is scoped to shared_with=request.user, so
        # a share that isn't theirs simply isn't found.
        self.assertEqual(response.status_code, 404)
        self.assertFalse(FolderItem.objects.filter(folder=other_folder).exists())

    def test_cannot_view_another_lectors_folder(self):
        folder = Folder.objects.create(owner=self.lector, name="Mine")
        self.client.login(username="lfc_other", password="pass12345")
        response = self.client.get(reverse("notes:folder-detail", args=[folder.pk]))
        self.assertEqual(response.status_code, 404)


class LectorCannotMutateNotesTests(TestCase):
    def setUp(self):
        self.editor = User.objects.create_user(
            username="lcm_editor", password="pass12345", role="editor"
        )
        self.lector = User.objects.create_user(
            username="lcm_lector", password="pass12345", role="lector"
        )
        self.note = Note.objects.create(
            owner=self.editor, title="Original title", content="original content"
        )
        Share.objects.create(note=self.note, shared_with=self.lector)

    def test_lector_post_to_editor_update_url_is_forbidden(self):
        self.client.login(username="lcm_lector", password="pass12345")
        response = self.client.post(
            reverse("notes:note-update", args=[self.note.pk]),
            {"title": "Hacked", "content": "hacked content"},
        )
        self.assertEqual(response.status_code, 403)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, "Original title")
        self.assertEqual(self.note.content, "original content")

    def test_lector_post_to_editor_delete_url_is_forbidden(self):
        self.client.login(username="lcm_lector", password="pass12345")
        response = self.client.post(reverse("notes:note-delete", args=[self.note.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Note.objects.filter(pk=self.note.pk).exists())
