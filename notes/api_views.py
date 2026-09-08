from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin

from .models import Category
from .serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    """Category CRUD. Read access is open to any authenticated user (Editors
    need to read categories to assign them to notes); write access
    (create/update/destroy) is restricted to Admins, mirroring the MVT
    Category views.
    """

    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
