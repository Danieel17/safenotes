from django.urls import path

from . import admin_views, views

urlpatterns = [
    path("login/", views.SafeNotesLoginView.as_view(), name="login"),
    path("logout/", views.SafeNotesLogoutView.as_view(), name="logout"),
    path("admin-panel/", admin_views.AdminPanelView.as_view(), name="admin-panel"),
    path("admin-panel/users/", admin_views.UserListView.as_view(), name="user-list"),
    path("admin-panel/users/create/", admin_views.UserCreateView.as_view(), name="user-create"),
    path("admin-panel/users/<int:pk>/toggle-active/", admin_views.UserToggleActiveView.as_view(), name="user-toggle-active"),
    path("admin-panel/users/<int:pk>/role/", admin_views.UserRoleChangeView.as_view(), name="user-role-change"),
]
