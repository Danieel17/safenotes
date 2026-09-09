"""DRF permission classes for role-based access control.

This module provides DRF-idiom role checks for API views/viewsets, using
``permission_classes = [IsAuthenticated, IsAdmin]`` list syntax.

We use concrete subclasses (IsAdmin, IsEditor, IsLector) rather than a
parametrized factory (e.g. ``IsRole('admin')``) because DRF's declarative
``permission_classes`` list expects classes, not instances, which makes a
factory awkward to use directly in that syntax.

These only check the user's *role* -- they do not perform per-object
ownership filtering. Each view/viewset remains responsible for filtering
its own queryset.
"""
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow access only to authenticated users with the 'admin' role."""

    def has_permission(self, request, view):
        # Exige autenticado + rol admin, en ese orden.
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsEditor(BasePermission):
    """Allow access only to authenticated users with the 'editor' role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "editor"
        )


class IsLector(BasePermission):
    """Allow access only to authenticated users with the 'lector' role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "lector"
        )
