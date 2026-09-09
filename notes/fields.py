from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


def _get_fernet():
    # La key se lee desde settings (NOTES_ENCRYPTION_KEY). Aceptamos
    # str o bytes y normalizamos a bytes para Fernet.
    key = settings.NOTES_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class EncryptedTextField(models.TextField):
    """A TextField that transparently encrypts/decrypts its value.

    The plaintext is encrypted with Fernet (symmetric, authenticated)
    before being written to the database, and decrypted when read back.
    From the model's perspective the field always behaves like a plain
    ``str`` - encryption/decryption is invisible to calling code.
    """

    def get_prep_value(self, value):
        if value is None:
            return value
        if not isinstance(value, str):
            value = str(value)
        token = _get_fernet().encrypt(value.encode())
        return token.decode()

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        return _get_fernet().decrypt(value.encode()).decode()
