from django.urls import path

from . import views

app_name = "notes"

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("categories/create/", views.CategoryCreateView.as_view(), name="category-create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category-update"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category-delete"),

    path("", views.NoteListView.as_view(), name="note-list"),
    path("create/", views.NoteCreateView.as_view(), name="note-create"),
    path("<int:pk>/", views.NoteDetailView.as_view(), name="note-detail"),
    path("<int:pk>/edit/", views.NoteUpdateView.as_view(), name="note-update"),
    path("<int:pk>/delete/", views.NoteDeleteView.as_view(), name="note-delete"),
    path("<int:pk>/share/", views.NoteShareCreateView.as_view(), name="note-share"),
    path("<int:pk>/share/<int:share_pk>/delete/", views.NoteShareDeleteView.as_view(), name="note-unshare"),

    path("shared/", views.SharedNoteListView.as_view(), name="shared-note-list"),
    path("shared/<int:share_pk>/", views.SharedNoteDetailView.as_view(), name="shared-note-detail"),
    path("shared/<int:share_pk>/add-to-folder/", views.AddShareToFolderView.as_view(), name="shared-note-add-to-folder"),

    path("folders/", views.FolderListView.as_view(), name="folder-list"),
    path("folders/create/", views.FolderCreateView.as_view(), name="folder-create"),
    path("folders/<int:pk>/", views.FolderDetailView.as_view(), name="folder-detail"),
    path("folders/<int:pk>/edit/", views.FolderUpdateView.as_view(), name="folder-update"),
    path("folders/<int:pk>/delete/", views.FolderDeleteView.as_view(), name="folder-delete"),
]
