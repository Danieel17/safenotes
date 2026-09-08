from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from audit.models import AuditLog
from audit.services import log_action

from .models import User
from .permissions import IsAdmin
from .serializers import (
    LockoutAwareTokenObtainPairSerializer,
    ProfileSerializer,
    UserCreateSerializer,
    UserListSerializer,
)


class SafeNotesTokenObtainPairView(TokenObtainPairView):
    """Login endpoint using the lockout-aware serializer.

    DRF's GenericAPIView.get_serializer_context() already includes
    "request" by default, which is what LockoutAwareTokenObtainPairSerializer
    relies on for audit logging and IP extraction.
    """

    serializer_class = LockoutAwareTokenObtainPairSerializer


class LogoutView(APIView):
    """Blacklist the given refresh token and log the logout."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_str = request.data.get("refresh")
        if not refresh_str:
            return Response(
                {"detail": "El campo 'refresh' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_str)
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Token de actualización inválido o expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log_action(
            actor=request.user,
            action=AuditLog.ACTION_LOGOUT,
            target_repr=f"User:{request.user.username}",
            request=request,
        )

        return Response(status=status.HTTP_205_RESET_CONTENT)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Self-service profile view/update - always operates on request.user."""

    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListCreateView(generics.ListCreateAPIView):
    """Admin-only user management: list all users, create editor/lector users."""

    queryset = User.objects.all().order_by("username")
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserListSerializer

    def perform_create(self, serializer):
        new_user = serializer.save()
        log_action(
            actor=self.request.user,
            action=AuditLog.ACTION_USER_CREATED,
            target_repr=f"User:{new_user.username}",
            request=self.request,
        )


class UserToggleActiveView(APIView):
    """POST-only: toggle a user's is_active flag. Admin accounts are protected.

    Mirrors accounts.admin_views.UserToggleActiveView. The AuditLog action
    vocabulary only defines ``user_deactivated`` (no distinct "reactivated"
    code); both directions are logged under that action code, with the
    direction made explicit in target_repr (e.g. "User:bob -> inactive").
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target.role == User.ROLE_ADMIN:
            return Response(
                {"detail": "No se puede modificar una cuenta de Admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        log_action(
            actor=request.user,
            action=AuditLog.ACTION_USER_DEACTIVATED,
            target_repr=f"User:{target.username} -> {'active' if target.is_active else 'inactive'}",
            request=request,
        )
        return Response(UserListSerializer(target).data)


class UserRoleChangeView(APIView):
    """POST-only: change a user's role between editor/lector. Admin accounts are protected."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target.role == User.ROLE_ADMIN:
            return Response(
                {"detail": "No se puede modificar una cuenta de Admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_role = request.data.get("role")
        if new_role not in [User.ROLE_EDITOR, User.ROLE_LECTOR]:
            return Response(
                {"detail": "El rol debe ser 'editor' o 'lector'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        target.role = new_role
        target.save(update_fields=["role"])
        log_action(
            actor=request.user,
            action=AuditLog.ACTION_USER_ROLE_CHANGED,
            target_repr=f"User:{target.username} -> {new_role}",
            request=request,
        )
        return Response(UserListSerializer(target).data)
