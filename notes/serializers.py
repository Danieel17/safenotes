from rest_framework import serializers

from .models import Category, Folder, Note, Share


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


class SharedNoteSerializer(serializers.ModelSerializer):
    """Read-only representation of a ``Share`` row from the Lector's point of
    view - exposes the underlying note's data. ``id`` here is the share id
    (used as the lookup key for detail/add-to-folder), not the note id.
    """

    note_title = serializers.CharField(source="note.title", read_only=True)
    note_content = serializers.CharField(source="note.content", read_only=True)
    note_category = serializers.CharField(
        source="note.category.name", read_only=True, allow_null=True, default=None
    )
    owner_username = serializers.CharField(source="note.owner.username", read_only=True)

    class Meta:
        model = Share
        fields = [
            "id",
            "note_title",
            "note_content",
            "note_category",
            "owner_username",
            "created_at",
        ]


class FolderSerializer(serializers.ModelSerializer):
    """Folder CRUD serializer. ``owner`` is set by the view (not here) from
    ``request.user`` on create - it is read-only here.
    """

    owner = serializers.StringRelatedField(read_only=True)
    items = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ["id", "name", "owner", "created_at", "items"]

    def get_items(self, obj):
        return [
            {
                "folder_item_id": item.pk,
                "share_id": item.share_id,
                "note_title": item.share.note.title,
            }
            for item in obj.items.select_related("share__note").all()
        ]
