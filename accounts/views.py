from django.contrib.auth.views import LoginView, LogoutView

from audit.models import AuditLog
from audit.services import log_action

from .forms import LockoutAwareAuthenticationForm


class SafeNotesLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LockoutAwareAuthenticationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.get_user()
        log_action(
            actor=user,
            action=AuditLog.ACTION_LOGIN,
            target_repr=f"User:{user.username}",
            request=self.request,
        )
        return response

    def get_success_url(self):
        # Admin gets its own landing page (the admin panel); editor and
        # lector still redirect to the shared home page until later
        # tickets give them role-specific landing pages.
        role = getattr(self.request.user, "role", None)
        role_redirects = {
            "admin": "/admin-panel/",
            "editor": "/notes/",
            "lector": "/notes/shared/",
        }
        return role_redirects.get(role, "/")


class SafeNotesLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        # Capture the user before Django's LogoutView clears request.user,
        # so we can still log who logged out.
        user = request.user if request.user.is_authenticated else None
        response = super().dispatch(request, *args, **kwargs)
        if user is not None:
            log_action(
                actor=user,
                action=AuditLog.ACTION_LOGOUT,
                target_repr=f"User:{user.username}",
                request=request,
            )
        return response
