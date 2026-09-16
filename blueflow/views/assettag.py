"""Join table for assets and tags."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, viewsets
from rest_framework.fields import IntegerField

from blueflow.models import AssetTag

from .tag import TagSerializer
from .utils import ChangeReasonMixin, HugeLimitOffsetPagination


class AssetTagSerializer(serializers.ModelSerializer):
    """Serializes AssetTag objects."""

    tag = TagSerializer(read_only=True)
    asset_id = IntegerField()
    tag_id = IntegerField()

    class Meta:
        model = AssetTag
        fields = (
            "id",
            "asset_id",
            "tag_id",
            "date_added",
            "provenance",
            "tag",
        )


@extend_schema(exclude=True)
class AssetTagViewSet(ChangeReasonMixin, viewsets.ModelViewSet):
    """An AssetTag links a tag to an asset."""

    queryset = AssetTag.objects.all()
    serializer_class = AssetTagSerializer
    pagination_class = HugeLimitOffsetPagination
