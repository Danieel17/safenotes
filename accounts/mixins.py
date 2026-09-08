from django.http import HttpResponseForbidden


class RoleRequiredMixin:
    """Restrict a class-based view to one or more user roles.

    Meant to be combined with Django's ``LoginRequiredMixin`` (put it
    first in the MRO, e.g. ``class MyView(LoginRequiredMixin,
    RoleRequiredMixin, View)``). ``LoginRequiredMixin`` is responsible for
    the anonymous-user case (redirect to login); this mixin only handles
    the "authenticated but wrong role" case, returning a plain
    ``HttpResponseForbidden`` (403) rather than a redirect.

    Configure with either:
      - ``required_role = "admin"`` for a single allowed role, or
      - ``required_roles = ["admin", "editor"]`` for several.

    If ``required_roles`` is set it takes precedence; otherwise
    ``required_role`` is wrapped into a single-item list.

    IMPORTANT: this mixin only checks the user's *role*. It does NOT do
    per-object ownership filtering (e.g. an Editor viewing or editing
    another Editor's note). Each view remains responsible for filtering
    its own queryset (e.g. ``queryset.filter(owner=request.user)``) to
    enforce ownership - that is implemented per-view in later tickets.
    """

    required_role = None
    required_roles = None

    def get_required_roles(self):
        if self.required_roles is not None:
            return list(self.required_roles)
        return [self.required_role]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.role not in self.get_required_roles():
                return HttpResponseForbidden(
                    "You do not have permission to access this page."
                )
        return super().dispatch(request, *args, **kwargs)
