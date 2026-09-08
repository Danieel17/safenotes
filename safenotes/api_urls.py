"""URL configuration for the /api/ surface (DRF).

Ticket 02 adds JWT auth (login/refresh/logout) and the self-service
profile endpoint. Further endpoints are added in tickets 03-05.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.api_views import LogoutView, ProfileView, SafeNotesTokenObtainPairView

router = DefaultRouter()

urlpatterns = router.urls + [
    path("auth/token/", SafeNotesTokenObtainPairView.as_view(), name="api-token-obtain-pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="api-token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="api-logout"),
    path("profile/", ProfileView.as_view(), name="api-profile"),
]
