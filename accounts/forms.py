from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from audit.models import AuditLog
from audit.services import log_action

from .models import User


class LockoutAwareAuthenticationForm(AuthenticationForm):
    """Login form with brute-force lockout and audit logging.

    Django's default ``AuthenticationForm.clean()`` calls ``authenticate()``
    first and only afterwards runs ``confirm_login_allowed()``. The ticket
    calls for checking the lock status *before* touching the password at
    all, so the whole ``clean()`` method is overridden rather than just
    ``confirm_login_allowed()``.
    """

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if not username or not password:
            return super().clean()

        existing_user = User.objects.filter(username=username).first()

        # 1. Lock check happens before any password verification so a
        # locked-out attempt never reveals whether the password was right.
        if (
            existing_user is not None
            and existing_user.locked_until is not None
            and existing_user.locked_until > timezone.now()
        ):
            log_action(
                actor=existing_user,
                action=AuditLog.ACTION_LOGIN_FAILED,
                target_repr=f"User:{username}",
                request=self.request,
            )
            raise forms.ValidationError(
                "Cuenta bloqueada temporalmente por múltiples intentos "
                "fallidos. Intenta nuevamente más tarde.",
                code="locked",
            )

        # 2. Normal password check.
        self.user_cache = authenticate(
            self.request, username=username, password=password
        )

        if self.user_cache is None:
            if existing_user is not None:
                existing_user.failed_login_count += 1
                if existing_user.failed_login_count >= settings.LOGIN_LOCKOUT_THRESHOLD:
                    existing_user.locked_until = timezone.now() + timedelta(
                        minutes=settings.LOGIN_LOCKOUT_MINUTES
                    )
                existing_user.save(update_fields=["failed_login_count", "locked_until"])

            # actor is None when the username doesn't exist at all - we
            # still record the attempted username in target_repr.
            log_action(
                actor=existing_user,
                action=AuditLog.ACTION_LOGIN_FAILED,
                target_repr=f"User:{username}",
                request=self.request,
            )
            raise self.get_invalid_login_error()

        # Successful authentication: run the remaining Django checks
        # (e.g. is_active) then reset the failure counter.
        self.confirm_login_allowed(self.user_cache)

        if existing_user.failed_login_count or existing_user.locked_until:
            existing_user.failed_login_count = 0
            existing_user.locked_until = None
            existing_user.save(update_fields=["failed_login_count", "locked_until"])

        return self.cleaned_data


class AdminUserCreationForm(forms.Form):
    """Form used by an Admin to create a new Editor or Lector user.

    Role choices are deliberately restricted to editor/lector - an Admin
    account can only be created via ``createsuperuser`` or Django's own
    ``/admin/`` site, never through this UI.
    """

    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(
        choices=[(User.ROLE_EDITOR, "Editor"), (User.ROLE_LECTOR, "Lector")]
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def save(self):
        user = User(username=self.cleaned_data["username"], role=self.cleaned_data["role"])
        user.set_password(self.cleaned_data["password"])
        user.save()
        return user


class UserRoleChangeForm(forms.Form):
    """Change a non-admin user's role between editor and lector."""

    role = forms.ChoiceField(
        choices=[(User.ROLE_EDITOR, "Editor"), (User.ROLE_LECTOR, "Lector")]
    )
