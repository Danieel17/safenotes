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
