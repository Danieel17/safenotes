from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SafeNotesUserAdmin(UserAdmin):
    """Developer-convenience admin registration for the custom User model.

    Extends Django's built-in UserAdmin (rather than replacing it) so the
    username/password change forms and existing behavior keep working.
    This is only for developers using /admin/ during development - the
    app's own Admin-role user management screens are a separate, later
    ticket.
    """

    fieldsets = UserAdmin.fieldsets + (
        ("SafeNotes", {"fields": ("role", "failed_login_count", "locked_until")}),
    )
    list_display = UserAdmin.list_display + ("role", "failed_login_count", "locked_until")
    list_filter = UserAdmin.list_filter + ("role",)
