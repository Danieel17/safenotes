from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from audit.models import AuditLog
from audit.services import log_action

from .serializers import LockoutAwareTokenObtainPairSerializer, ProfileSerializer


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
