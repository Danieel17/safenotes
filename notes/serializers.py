from rest_framework import serializers

from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    """Category CRUD serializer. ``created_by`` is set by the view (not here)
    from ``request.user`` on create - it is read-only in the serializer.
    """

    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "created_by"]
