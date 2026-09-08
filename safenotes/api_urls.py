"""URL configuration for the /api/ surface (DRF).

Empty for now — this file exists only to prove the /api/ prefix resolves
without error. Real endpoints are added in tickets 02-05.
"""
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = router.urls
