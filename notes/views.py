from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.mixins import RoleRequiredMixin

from .models import Category


class AdminOnlyMixin(LoginRequiredMixin, RoleRequiredMixin):
    required_role = "admin"


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
