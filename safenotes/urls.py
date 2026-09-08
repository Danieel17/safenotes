"""
URL configuration for safenotes project.
"""
from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('notes/', include('notes.urls')),
    path('audit/', include('audit.urls')),
    path('', views.home, name='home'),
]
