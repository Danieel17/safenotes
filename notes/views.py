from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.mixins import RoleRequiredMixin
from accounts.models import User
from audit.models import AuditLog
from audit.services import log_action

from .models import Category, Folder, FolderItem, Note, Share


class AdminOnlyMixin(LoginRequiredMixin, RoleRequiredMixin):
    required_role = "admin"


class EditorOnlyMixin(LoginRequiredMixin, RoleRequiredMixin):
    required_role = "editor"


class LectorOnlyMixin(LoginRequiredMixin, RoleRequiredMixin):
    required_role = "lector"


class CategoryListView(AdminOnlyMixin, ListView):
    model = Category
    template_name = "notes/category_list.html"
    context_object_name = "categories"


class CategoryCreateView(AdminOnlyMixin, CreateView):
    model = Category
    fields = ["name"]
    template_name = "notes/category_form.html"
    success_url = reverse_lazy("notes:category-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class CategoryUpdateView(AdminOnlyMixin, UpdateView):
    model = Category
    fields = ["name"]
    template_name = "notes/category_form.html"
    success_url = reverse_lazy("notes:category-list")


class CategoryDeleteView(AdminOnlyMixin, DeleteView):
    model = Category
    template_name = "notes/category_confirm_delete.html"
    success_url = reverse_lazy("notes:category-list")


# --- Editor note CRUD -------------------------------------------------

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["title", "content", "category"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 10}),
        }


class ShareForm(forms.Form):
    shared_with = forms.ModelChoiceField(
        queryset=User.objects.filter(role="lector"),
        label="Compartir con (lector)",
    )


class NoteListView(EditorOnlyMixin, ListView):
    model = Note
    template_name = "notes/note_list.html"
    context_object_name = "notes"

    def get_queryset(self):
        return Note.objects.filter(owner=self.request.user)


class NoteCreateView(EditorOnlyMixin, CreateView):
    model = Note
    form_class = NoteForm
    template_name = "notes/note_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        log_action(
            actor=self.request.user,
            action=AuditLog.ACTION_NOTE_CREATED,
            target_repr=f"Note:{self.object.pk}",
            request=self.request,
        )
        return response

    def get_success_url(self):
        return reverse("notes:note-detail", args=[self.object.pk])


class NoteDetailView(EditorOnlyMixin, DetailView):
    model = Note
    template_name = "notes/note_detail.html"
    context_object_name = "note"

    def get_queryset(self):
        return Note.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shares"] = self.object.shares.select_related("shared_with")
        context["share_form"] = ShareForm()
        return context


class NoteUpdateView(EditorOnlyMixin, UpdateView):
    model = Note
    form_class = NoteForm
    template_name = "notes/note_form.html"

    def get_queryset(self):
        return Note.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            actor=self.request.user,
            action=AuditLog.ACTION_NOTE_UPDATED,
            target_repr=f"Note:{self.object.pk}",
            request=self.request,
        )
        return response

    def get_success_url(self):
        return reverse("notes:note-detail", args=[self.object.pk])


class NoteDeleteView(EditorOnlyMixin, DeleteView):
    model = Note
    template_name = "notes/note_confirm_delete.html"
    success_url = reverse_lazy("notes:note-list")

    def get_queryset(self):
        return Note.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        note_pk = self.object.pk
        response = super().form_valid(form)
        log_action(
            actor=self.request.user,
            action=AuditLog.ACTION_NOTE_DELETED,
            target_repr=f"Note:{note_pk}",
            request=self.request,
        )
        return response


class NoteShareCreateView(EditorOnlyMixin, View):
    """Create a Share for a note. Re-verifies ownership via an
    owner-filtered queryset instead of trusting the note pk in the URL
    alone, so a non-owner can't share someone else's note."""

    def post(self, request, pk):
        note = get_object_or_404(Note, pk=pk, owner=request.user)
        form = ShareForm(request.POST)
        if form.is_valid():
            target = form.cleaned_data["shared_with"]
            if Share.objects.filter(note=note, shared_with=target).exists():
                messages.info(request, "Esta nota ya está compartida con ese usuario.")
            else:
                try:
                    Share.objects.create(note=note, shared_with=target)
                except IntegrityError:
                    messages.info(request, "Esta nota ya está compartida con ese usuario.")
                else:
                    log_action(
                        actor=request.user,
                        action=AuditLog.ACTION_NOTE_SHARED,
                        target_repr=f"Note:{note.pk} -> User:{target.username}",
                        request=request,
                    )
                    messages.success(request, f"Nota compartida con {target.username}.")
        else:
            messages.error(request, "Selecciona un lector válido.")
        return redirect("notes:note-detail", pk=note.pk)


class NoteShareDeleteView(EditorOnlyMixin, View):
    """Delete a Share. No AuditLog action exists for "unshare" in the
    current action vocabulary, so this is intentionally not logged (a
    later ticket can add one if audit coverage needs to grow)."""

    def post(self, request, pk, share_pk):
        note = get_object_or_404(Note, pk=pk, owner=request.user)
        share = get_object_or_404(Share, pk=share_pk, note=note)
        share.delete()
        messages.success(request, "Se dejó de compartir la nota.")
        return redirect("notes:note-detail", pk=note.pk)


# --- Lector: shared notes (read-only) & personal folders CRUD --------

class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ["name"]


class AddToFolderForm(forms.Form):
    folder = forms.ModelChoiceField(queryset=Folder.objects.none(), label="Carpeta")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["folder"].queryset = Folder.objects.filter(owner=user)


class SharedNoteListView(LectorOnlyMixin, ListView):
    """Notes shared with the requesting Lector - read-only."""

    model = Share
    template_name = "notes/shared_note_list.html"
    context_object_name = "shares"

    def get_queryset(self):
        return (
            Share.objects.filter(shared_with=self.request.user)
            .select_related("note", "note__owner", "note__category")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["folders"] = Folder.objects.filter(owner=self.request.user)
        return context


class SharedNoteDetailView(LectorOnlyMixin, DetailView):
    """Read-only view of a note via the Share the Lector holds.

    Resolved strictly through a ``Share`` filtered on ``shared_with`` (not
    a raw ``Note.objects.get(pk=...)``) so a Lector can't view a note by
    guessing its Note pk if it wasn't actually shared with them.
    """

    template_name = "notes/shared_note_detail.html"
    context_object_name = "share"
    pk_url_kwarg = "share_pk"

    def get_queryset(self):
        return Share.objects.filter(shared_with=self.request.user).select_related(
            "note", "note__owner", "note__category"
        )

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        log_action(
            actor=request.user,
            action=AuditLog.ACTION_NOTE_VIEWED,
            target_repr=f"Note:{self.object.note.pk}",
            request=request,
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["note"] = self.object.note
        context["add_to_folder_form"] = AddToFolderForm(user=self.request.user)
        return context


class AddShareToFolderView(LectorOnlyMixin, View):
    """Link a Share the Lector holds into one of their own Folders.

    Both the Folder (owner=request.user) and the Share (shared_with=
    request.user) are re-verified from the database rather than trusted
    from hidden form fields, so a Lector can't graft another Lector's
    Share into their folder, or target a Folder they don't own.
    """

    def post(self, request, share_pk):
        share = get_object_or_404(Share, pk=share_pk, shared_with=request.user)
        form = AddToFolderForm(request.POST, user=request.user)
        if form.is_valid():
            folder = form.cleaned_data["folder"]
            # Re-check ownership even though the queryset was already
            # scoped, and guard the unique_together with check-then-create.
            if not Folder.objects.filter(pk=folder.pk, owner=request.user).exists():
                messages.error(request, "Carpeta inválida.")
            elif FolderItem.objects.filter(folder=folder, share=share).exists():
                messages.info(request, "Esa nota ya está en esa carpeta.")
            else:
                try:
                    FolderItem.objects.create(folder=folder, share=share)
                except IntegrityError:
                    messages.info(request, "Esa nota ya está en esa carpeta.")
                else:
                    messages.success(request, f"Nota agregada a '{folder.name}'.")
        else:
            messages.error(request, "Selecciona una carpeta válida.")
        return redirect("notes:shared-note-detail", share_pk=share.pk)


class FolderListView(LectorOnlyMixin, ListView):
    model = Folder
    template_name = "notes/folder_list.html"
    context_object_name = "folders"

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user)


class FolderCreateView(LectorOnlyMixin, CreateView):
    model = Folder
    form_class = FolderForm
    template_name = "notes/folder_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("notes:folder-detail", args=[self.object.pk])


class FolderDetailView(LectorOnlyMixin, DetailView):
    model = Folder
    template_name = "notes/folder_detail.html"
    context_object_name = "folder"

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items.select_related(
            "share", "share__note", "share__note__owner"
        )
        return context


class FolderUpdateView(LectorOnlyMixin, UpdateView):
    model = Folder
    form_class = FolderForm
    template_name = "notes/folder_form.html"

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user)

    def get_success_url(self):
        return reverse("notes:folder-detail", args=[self.object.pk])


class FolderDeleteView(LectorOnlyMixin, DeleteView):
    model = Folder
    template_name = "notes/folder_confirm_delete.html"
    success_url = reverse_lazy("notes:folder-list")

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user)
