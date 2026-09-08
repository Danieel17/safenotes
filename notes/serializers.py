from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Category, Folder, Note, Share

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Category CRUD serializer. ``created_by`` is set by the view (not here)
    from ``request.user`` on create - it is read-only in the serializer.
    """

    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "created_by"]


class NoteShareSerializer(serializers.ModelSerializer):
    """Read-only representation of a ``Share`` row from the note owner's
    (Editor's) point of view - nested into ``NoteSerializer`` so the note
    detail response lists who it's currently shared with, without exposing a
    separate listing endpoint.
    """

    shared_with_username = serializers.CharField(source="shared_with.username", read_only=True)

    class Meta:
        model = Share
        fields = ["id", "shared_with", "shared_with_username", "created_at"]


class NoteSerializer(serializers.ModelSerializer):
    """Note CRUD serializer. ``owner`` is intentionally NOT a field here - it
    is set server-side by the view from ``request.user`` and must never be
    accepted from client input (would otherwise allow spoofing ownership).

    ``shares`` is a read-only nested list of the note's current shares, added
    so the Editor UI can show/manage them from the note detail response
    without a dedicated shares-listing endpoint.
    """

    shares = NoteShareSerializer(many=True, read_only=True)

    class Meta:
        model = Note
        fields = ["id", "title", "content", "category", "created_at", "updated_at", "shares"]


class ShareSerializer(serializers.ModelSerializer):
    """Validates the target of a share/unshare action. Mirrors the MVT
    ``ShareForm``'s restriction that notes may only be shared with users
    who have the 'lector' role.

    Accepts the target either as ``shared_with`` (numeric user id, the
    original contract) or as ``shared_with_username`` (a write-only
    convenience field resolved to the ``User`` here) - the React Editor UI
    only knows the target lector's username, not their id, and there is
    deliberately no general user-listing endpoint available to Editors.
    """

    shared_with_username = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Share
        fields = ["id", "shared_with", "shared_with_username", "created_at"]
        extra_kwargs = {"shared_with": {"required": False}}

    def validate(self, attrs):
        shared_with = attrs.get("shared_with")
        username = attrs.pop("shared_with_username", None)

        if shared_with is None and username:
            try:
                shared_with = User.objects.get(username=username)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"shared_with_username": "No existe un usuario con ese nombre."}
                )
            attrs["shared_with"] = shared_with

        if shared_with is None:
            raise serializers.ValidationError(
                {"shared_with": "Debe indicar el usuario destino (id o username)."}
            )

        if shared_with.role != "lector":
            raise serializers.ValidationError(
                {"shared_with": "Las notas solo pueden compartirse con usuarios lectores."}
            )

        return attrs


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
