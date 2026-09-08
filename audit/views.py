from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from accounts.mixins import RoleRequiredMixin

from .models import AuditLog


class AuditLogListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    required_role = "admin"
    model = AuditLog
    template_name = "audit/auditlog_list.html"
    context_object_name = "logs"
    paginate_by = 25

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("actor").order_by("-timestamp")
        action = self.request.GET.get("action")
        actor = self.request.GET.get("actor")
        if action:
            queryset = queryset.filter(action=action)
        if actor:
            queryset = queryset.filter(actor__username=actor)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action_filter"] = self.request.GET.get("action", "")
        context["actor_filter"] = self.request.GET.get("actor", "")
        context["action_choices"] = AuditLog.ACTION_CHOICES
        return context
