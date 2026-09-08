"""Model-level tests independent of any view layer.

The MVT view-based tests that used to live here were removed in ticket 10
along with the old template views; that behavior is now covered by
notes/tests_api.py. NoteEncryptionTests is kept because it exercises
EncryptedTextField / Note model behavior directly against the database and
has no equivalent in the API test suite.
"""
from django.db import connection

from django.test import TestCase

from accounts.models import User

from .models import Note


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
