from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdmin, IsEditor, IsLector
from audit.services import log_action

from .models import Category, Folder, FolderItem, Note, Share
from .serializers import (
    CategorySerializer,
    FolderSerializer,
    NoteSerializer,
    ShareSerializer,
    SharedNoteSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """Category CRUD. Read access is open to any authenticated user (Editors
    need to read categories to assign them to notes); write access
    (create/update/destroy) is restricted to Admins, mirroring the MVT
    Category views.
    """

    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class NoteViewSet(viewsets.ModelViewSet):
    """Editor-only note CRUD plus sharing actions.

    ``get_queryset`` is filtered to notes owned by the requesting user - this
    is the IDOR-prevention mechanism: DRF's generic ``get_object()`` (used by
    retrieve/update/destroy/partial_update and by the ``share``/``unshare``
    actions below via ``self.get_object()``) raises Http404 for a pk that
    exists but belongs to another editor, rather than leaking its existence
    via a 403.
    """

    permission_classes = [IsAuthenticated, IsEditor]
    serializer_class = NoteSerializer

    def get_queryset(self):
        return Note.objects.filter(owner=self.request.user).order_by("-updated_at")

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)
        log_action(
            actor=self.request.user,
            action="note_created",
            target_repr=f"Note:{instance.pk}",
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            actor=self.request.user,
            action="note_updated",
            target_repr=f"Note:{instance.pk}",
            request=self.request,
        )

    def perform_destroy(self, instance):
        target_repr = f"Note:{instance.pk}"
        instance.delete()
        log_action(
            actor=self.request.user,
            action="note_deleted",
            target_repr=target_repr,
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def share(self, request, pk=None):
        note = self.get_object()
        serializer = ShareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shared_with = serializer.validated_data["shared_with"]

        if Share.objects.filter(note=note, shared_with=shared_with).exists():
            return Response(
                {"detail": "Ya estaba compartida con este usuario."},
                status=status.HTTP_200_OK,
            )

        try:
            Share.objects.create(note=note, shared_with=shared_with)
        except IntegrityError:
            # Defense-in-depth against a race between the exists() check
            # above and the create() call hitting the unique_together
            # constraint - fall back to the same graceful response instead
            # of a 500.
            return Response(
                {"detail": "Ya estaba compartida con este usuario."},
                status=status.HTTP_200_OK,
            )

        log_action(
            actor=request.user,
            action="note_shared",
            target_repr=f"Note:{note.pk} -> User:{shared_with.username}",
            request=request,
        )
        return Response({"detail": "Nota compartida."}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def unshare(self, request, pk=None):
        note = self.get_object()
        shared_with_id = request.data.get("shared_with")
        deleted, _ = Share.objects.filter(
            note=note, shared_with_id=shared_with_id
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"detail": "No existe un share con ese usuario."},
            status=status.HTTP_404_NOT_FOUND,
        )


class SharedNoteViewSet(viewsets.ReadOnlyModelViewSet):
    """Lector-only read access to notes shared with them, plus the
    add-to-folder action. ``get_queryset`` is filtered to shares addressed to
    the requesting user - the same IDOR-prevention pattern as ``NoteViewSet``:
    a share id that exists but belongs to another lector 404s instead of
    leaking existence via a 403.
    """

    permission_classes = [IsAuthenticated, IsLector]
    serializer_class = SharedNoteSerializer

    def get_queryset(self):
        return Share.objects.filter(shared_with=self.request.user).select_related(
            "note", "note__owner", "note__category"
        ).order_by("-created_at")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        log_action(
            actor=request.user,
            action="note_viewed",
            target_repr=f"Note:{instance.note.pk}",
            request=request,
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="add-to-folder")
    def add_to_folder(self, request, pk=None):
        share = self.get_object()
        folder_id = request.data.get("folder_id")
        folder = Folder.objects.filter(pk=folder_id, owner=request.user).first()
        if folder is None:
            return Response(
                {"detail": "Carpeta no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if FolderItem.objects.filter(folder=folder, share=share).exists():
            return Response(
                {"detail": "Ya estaba en esa carpeta."},
                status=status.HTTP_200_OK,
            )

        try:
            FolderItem.objects.create(folder=folder, share=share)
        except IntegrityError:
            return Response(
                {"detail": "Ya estaba en esa carpeta."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "Nota agregada a la carpeta."}, status=status.HTTP_201_CREATED
        )


class FolderViewSet(viewsets.ModelViewSet):
    """Lector-owned folder CRUD. ``get_queryset`` is filtered to folders
    owned by the requesting user - the IDOR-prevention mechanism, same
    pattern as ``NoteViewSet``.
    """

    permission_classes = [IsAuthenticated, IsLector]
    serializer_class = FolderSerializer

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
