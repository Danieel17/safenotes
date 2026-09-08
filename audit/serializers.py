from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Read-only representation of an AuditLog row."""

    actor = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "action", "target_repr", "timestamp", "ip_address"]
        read_only_fields = fields
