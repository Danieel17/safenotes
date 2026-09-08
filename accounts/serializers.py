from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from audit.models import AuditLog
from audit.services import log_action

from .models import User


class LockoutAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login serializer replicating LockoutAwareAuthenticationForm's logic.

    Same ordering as the MVT form: check the lock status before touching
    the password at all, increment/reset the failure counter around the
    base simplejwt validation, and log every outcome via audit.services.log_action
    (the only sanctioned way to create AuditLog rows).
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        request = self.context.get("request")
        username = attrs.get("username")
        existing_user = User.objects.filter(username=username).first()

        # 1. Lock check happens before any password verification.
        if (
            existing_user is not None
            and existing_user.locked_until is not None
            and existing_user.locked_until > timezone.now()
        ):
            log_action(
                actor=existing_user,
                action=AuditLog.ACTION_LOGIN_FAILED,
                target_repr=f"User:{username}",
                request=request,
            )
            raise serializers.ValidationError(
                {
                    "detail": (
                        "Cuenta bloqueada temporalmente por múltiples intentos "
                        "fallidos. Intenta nuevamente más tarde."
                    )
                }
            )

        # 2. Normal credential check via simplejwt's base implementation.
        try:
            data = super().validate(attrs)
        except (AuthenticationFailed, Exception):
            if existing_user is not None:
                existing_user.failed_login_count += 1
                if existing_user.failed_login_count >= settings.LOGIN_LOCKOUT_THRESHOLD:
                    existing_user.locked_until = timezone.now() + timedelta(
                        minutes=settings.LOGIN_LOCKOUT_MINUTES
                    )
                existing_user.save(update_fields=["failed_login_count", "locked_until"])

            log_action(
                actor=existing_user,
                action=AuditLog.ACTION_LOGIN_FAILED,
                target_repr=f"User:{username}",
                request=request,
            )
            raise

        # 3. Successful authentication: reset the failure counter.
        if self.user.failed_login_count or self.user.locked_until:
            self.user.failed_login_count = 0
            self.user.locked_until = None
            self.user.save(update_fields=["failed_login_count", "locked_until"])

        log_action(
            actor=self.user,
            action=AuditLog.ACTION_LOGIN,
            target_repr=f"User:{self.user.username}",
            request=request,
        )

        return data


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "role"]
        read_only_fields = ["username", "role"]
