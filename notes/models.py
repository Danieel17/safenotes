from django.conf import settings
from django.db import models


class Category(models.Model):
    """Note category, managed exclusively by Admin users.

    Lives in the ``notes`` app (rather than ``accounts``) because a later
    ticket adds ``Note.category`` as a FK to this model - even though only
    Admins manage categories through the UI.
    """

    name = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_categories",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
