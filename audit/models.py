from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Immutable trail of security-relevant actions in SafeNotes.

    Rows should only ever be created via ``audit.services.log_action`` -
    that function is the single place that constructs AuditLog objects, so
    every caller gets consistent IP extraction and field population.
    """

    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_LOGIN_FAILED = "login_failed"
    ACTION_NOTE_CREATED = "note_created"
    ACTION_NOTE_VIEWED = "note_viewed"
    ACTION_NOTE_UPDATED = "note_updated"
    ACTION_NOTE_DELETED = "note_deleted"
    ACTION_NOTE_SHARED = "note_shared"
    ACTION_USER_CREATED = "user_created"
    ACTION_USER_ROLE_CHANGED = "user_role_changed"
    ACTION_USER_DEACTIVATED = "user_deactivated"
    ACTION_USER_DELETED = "user_deleted"

    ACTION_CHOICES = [
        (ACTION_LOGIN, "Login"),
        (ACTION_LOGOUT, "Logout"),
        (ACTION_LOGIN_FAILED, "Login failed"),
        (ACTION_NOTE_CREATED, "Note created"),
        (ACTION_NOTE_VIEWED, "Note viewed"),
        (ACTION_NOTE_UPDATED, "Note updated"),
        (ACTION_NOTE_DELETED, "Note deleted"),
        (ACTION_NOTE_SHARED, "Note shared"),
        (ACTION_USER_CREATED, "User created"),
        (ACTION_USER_ROLE_CHANGED, "User role changed"),
        (ACTION_USER_DEACTIVATED, "User deactivated"),
        (ACTION_USER_DELETED, "User deleted (self-service)"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    target_repr = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp} {self.actor} {self.action} {self.target_repr}"
