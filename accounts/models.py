from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model for SafeNotes.

    Role is a plain field (not Django Groups/Permissions) because SafeNotes
    has exactly three fixed, mutually exclusive roles and all authorization
    logic is simple "is this role allowed here" checks done via DRF
    permission classes (accounts.permissions) - Groups/Permissions would be
    unnecessary machinery for this scope.
    """

    ROLE_ADMIN = "admin"
    ROLE_EDITOR = "editor"
    ROLE_LECTOR = "lector"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_EDITOR, "Editor"),
        (ROLE_LECTOR, "Lector"),
    ]

    # Rol fijo del usuario: admin, editor o lector.
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    # Conteo de intentos de login fallidos (para el bloqueo por lockout).
    failed_login_count = models.PositiveSmallIntegerField(default=0)
    # Hasta cuando queda bloqueada la cuenta tras superar el umbral.
    locked_until = models.DateTimeField(null=True, blank=True)
