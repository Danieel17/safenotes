from django.conf import settings
from django.db import models

from .fields import EncryptedTextField


class Category(models.Model):
    """Note category, managed exclusively by Admin users.

    Lives in the ``notes`` app (rather than ``accounts``) because a later
    ticket adds ``Note.category`` as a FK to this model - even though only
    Admins manage categories through the UI.
    """

    # Nombre de la categoria; unique=True evita duplicados a nivel DB.
    name = models.CharField(max_length=100, unique=True)
    # Quien la creo (siempre un Admin). CASCADE borra las categorias con el usuario.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_categories",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Note(models.Model):
    """A note owned by a single user. ``content`` is encrypted at rest."""

    # Dueno de la nota. Cada editor solo ve/edita sus propias notas.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    title = models.CharField(max_length=200)
    # El contenido viaja cifrado en la DB (ver notes/fields.py).
    content = EncryptedTextField(blank=True, default="")
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Share(models.Model):
    """Grants ``shared_with`` access to a ``note``."""

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="shares")
    # Usuario lector que recibe el acceso a la nota.
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shared_notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Impide compartir la misma nota dos veces con el mismo usuario.
        unique_together = ("note", "shared_with")

    def __str__(self):
        return f"{self.note} -> {self.shared_with}"


class Folder(models.Model):
    """A user-owned collection of shared notes (via FolderItem)."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="folders",
    )
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class FolderItem(models.Model):
    """Places a ``Share`` (a note shared with the folder's owner) into a Folder."""

    # Carpeta que contiene la nota compartida (dueno = lector).
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="items")
    # El Share que se coloca en la carpeta.
    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name="folder_items")

    class Meta:
        # Una misma nota compartida no puede repetirse dentro de una carpeta.
        unique_together = ("folder", "share")

    def __str__(self):
        return f"{self.share} in {self.folder}"
