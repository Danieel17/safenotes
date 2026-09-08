from django.contrib import admin

from .models import Category, Folder, FolderItem, Note, Share


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "category", "created_at", "updated_at")
    fields = ("owner", "title", "content", "category", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("note", "shared_with", "created_at")


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")


@admin.register(FolderItem)
class FolderItemAdmin(admin.ModelAdmin):
    list_display = ("folder", "share")
