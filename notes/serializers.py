from rest_framework import serializers

from .models import Category, Note, Share


class CategorySerializer(serializers.ModelSerializer):
    """Category CRUD serializer. ``created_by`` is set by the view (not here)
    from ``request.user`` on create - it is read-only in the serializer.
    """

    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "created_by"]


class NoteSerializer(serializers.ModelSerializer):
    """Note CRUD serializer. ``owner`` is intentionally NOT a field here - it
    is set server-side by the view from ``request.user`` and must never be
    accepted from client input (would otherwise allow spoofing ownership).
    """

    class Meta:
        model = Note
        fields = ["id", "title", "content", "category", "created_at", "updated_at"]


class ShareSerializer(serializers.ModelSerializer):
    """Validates the target of a share/unshare action. Mirrors the MVT
    ``ShareForm``'s restriction that notes may only be shared with users
    who have the 'lector' role.
    """

    class Meta:
        model = Share
        fields = ["id", "shared_with", "created_at"]

    def validate_shared_with(self, value):
        if value.role != "lector":
            raise serializers.ValidationError(
                "Las notas solo pueden compartirse con usuarios lectores."
            )
        return value
