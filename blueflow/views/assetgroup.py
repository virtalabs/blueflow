"""Join table for assets and vulns."""

import typing

import django_filters
from drf_spectacular.utils import extend_schema
from rest_framework import response, serializers, status, viewsets
from rest_framework.fields import IntegerField

from blueflow.models import AssetGroup

from .group import GroupSerializer
from .utils import HugeLimitOffsetPagination


class AssetGroupSerializer(serializers.ModelSerializer):
    """Serializes AssetGroup objects."""

    # Few public methods; that's just how serializers work

    group = GroupSerializer(read_only=True)
    asset_id = IntegerField()
    group_id = IntegerField()

    class Meta:
        model = AssetGroup
        fields = (
            "id",
            "asset_id",
            "group_id",
            "date_added",
            "provenance",
            "group",
        )


class AssetGroupFilter(django_filters.rest_framework.FilterSet):
    """FilterSet."""

    class Meta:
        model = AssetGroup

        # https://docs.djangoproject.com/en/1.11/ref/models/querysets/#field-lookups
        fields: typing.ClassVar = {
            "asset": ["exact"],
            "group": ["exact"],
        }


@extend_schema(exclude=True)
class AssetGroupViewSet(viewsets.ModelViewSet):
    """An AssetGroup links a group to an asset."""

    queryset = AssetGroup.objects.all()
    serializer_class = AssetGroupSerializer
    filterset_class = AssetGroupFilter
    pagination_class = HugeLimitOffsetPagination
    http_method_names: typing.ClassVar = ["delete"]

    def get_object(self):
        """Allow get_object with asset / group combo.

        Regular get_object() expects a 'pk' kwarg.  We have another way,
        and thus need to override.
        """
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        if lookup_url_kwarg in self.kwargs:
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            obj = super().get_object(queryset, **filter_kwargs)
            return obj

        # We don't have 'pk'
        # Ensure we have one and only one AssetGroup, retrieved by
        # asset / group combo
        no_asset = "asset" not in self.request.query_params
        no_group = "group" not in self.request.query_params
        if no_asset and no_group:
            msg = "To DELETE one AssetGroup, specify both 'asset' and 'group'."
            raise response.Response(msg, status=status.HTTP_400_BAD_REQUEST)

        if queryset.count() > 1:
            msg = "Should only be possible to get 1 assetgroup here"
            raise ValueError(msg)

        obj = queryset.first()
        self.check_object_permissions(self.request, obj)
        return obj
