from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from audit.models import AuditLog
from audit.services import log_action

from .forms import AdminUserCreationForm, UserRoleChangeForm
from .mixins import RoleRequiredMixin
from .models import User


class AdminOnlyMixin(LoginRequiredMixin, RoleRequiredMixin):
    required_role = "admin"


class AdminPanelView(AdminOnlyMixin, View):
    """Landing page for the admin, linking to the management screens."""

    def get(self, request):
        return render(request, "accounts/admin_panel.html")


class UserListView(AdminOnlyMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"

    def get_queryset(self):
        return User.objects.all().order_by("username")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        context["now"] = now
        return context


class UserCreateView(AdminOnlyMixin, View):
    template_name = "accounts/user_form.html"

    def get(self, request):
        form = AdminUserCreationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            log_action(
                actor=request.user,
                action=AuditLog.ACTION_USER_CREATED,
                target_repr=f"User:{new_user.username}",
                request=request,
            )
            return redirect("user-list")
        return render(request, self.template_name, {"form": form})


class UserToggleActiveView(AdminOnlyMixin, View):
    """POST-only action toggling a user's is_active flag.

    Design choice: the AuditLog action vocabulary only defines
    ``user_deactivated`` (no distinct "reactivated" code). Rather than
    misusing that code for reactivation too, or leaving reactivation
    unlogged, we log both directions under ``user_deactivated`` but make
    the direction explicit in ``target_repr`` (e.g. "User:bob -> inactive"
    or "User:bob -> active"). This keeps every activity-status change
    auditable without inventing an action code the ticket didn't define.
    """

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.role == User.ROLE_ADMIN:
            return redirect("user-list")
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        log_action(
            actor=request.user,
            action=AuditLog.ACTION_USER_DEACTIVATED,
            target_repr=f"User:{user.username} -> {'active' if user.is_active else 'inactive'}",
            request=request,
        )
        return redirect("user-list")


class UserRoleChangeView(AdminOnlyMixin, View):
    template_name = "accounts/user_role_form.html"

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.role == User.ROLE_ADMIN:
            return redirect("user-list")
        form = UserRoleChangeForm(initial={"role": user.role})
        return render(request, self.template_name, {"form": form, "target_user": user})

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.role == User.ROLE_ADMIN:
            return redirect("user-list")
        form = UserRoleChangeForm(request.POST)
        if form.is_valid():
            new_role = form.cleaned_data["role"]
            user.role = new_role
            user.save(update_fields=["role"])
            log_action(
                actor=request.user,
                action=AuditLog.ACTION_USER_ROLE_CHANGED,
                target_repr=f"User:{user.username} -> {new_role}",
                request=request,
            )
            return redirect("user-list")
        return render(request, self.template_name, {"form": form, "target_user": user})
