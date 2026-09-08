from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """Admin-only, paginated audit log listing, filterable by ?action= and ?actor=.

    Mirrors audit.views.AuditLogListView's filtering logic.
    """

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("actor").order_by("-timestamp")
        action = self.request.query_params.get("action")
        actor = self.request.query_params.get("actor")
        if action:
            queryset = queryset.filter(action=action)
        if actor:
            queryset = queryset.filter(actor__username=actor)
        return queryset
