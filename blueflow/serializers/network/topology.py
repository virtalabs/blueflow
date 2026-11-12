import ipaddress
import typing

from rest_framework import serializers

from blueflow.models import Asset, System, SystemRequest
from blueflow.models.network import constants

Cidrs = list[ipaddress.IPv4Network | ipaddress.IPv6Network]


class TopologyRequestSerializer(serializers.Serializer):
    cidrs = serializers.ListField(required=False, child=serializers.CharField())
    network = serializers.CharField(required=False)
    scope = serializers.ChoiceField(
        choices=constants.ScopeChoices.choices, default=constants.ScopeChoices.boundary
    )

    def validate_scope(self, arg: str) -> constants.ScopeChoices:
        return constants.ScopeChoices(arg)

    def validate_cidrs(self, data: list[str]) -> Cidrs:
        cidrs = []
        for d in data:
            try:
                cidrs.append(ipaddress.ip_network(d))
            except ValueError as e:
                raise serializers.ValidationError from e
        return cidrs


class CidrField(serializers.Field):
    def to_internal_value(self, data: str) -> str:
        return str(data)


class QueryResponseSerializer(serializers.Serializer):
    cidrs = serializers.ListField(child=CidrField(), required=False)
    network = serializers.CharField(required=False)
    scope = serializers.ChoiceField(choices=constants.ScopeChoices.choices)


class AssetResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=0)
    hostname = serializers.CharField(allow_null=True)
    manufacturer = serializers.CharField(allow_blank=True)
    model = serializers.CharField(allow_blank=True)
    category = serializers.CharField(allow_blank=True)
    app_sw_version = serializers.CharField(allow_blank=True)

    def to_internal_value(self, data: "Asset") -> dict:
        return super().to_internal_value(data.__dict__)


class ConnectionResponseSerializer(serializers.Serializer):
    src_ip = serializers.CharField()
    dst_ip = serializers.CharField(allow_blank=True)
    dst_port = serializers.CharField()
    protocol = serializers.CharField()
    response_observed = serializers.BooleanField()
    service = serializers.CharField()

    def to_internal_value(self, data: SystemRequest) -> dict[str, typing.Any]:
        as_dict = {
            "src_ip": data.sender.ip_address,
            # receiver is temporarily nullable awaiting a new ingestion path
            "dst_ip": data.receiver.ip_address if data.receiver is not None else "",
            "dst_port": data.request.port,
            "protocol": data.request.protocol,
            "response_observed": data.request.response_seen,
            "service": data.request.service,
        }
        return super().to_internal_value(as_dict)


class ExternalEndpointsResponseSerializer(serializers.Serializer):
    ip_address = serializers.CharField()
    hostname = serializers.CharField(allow_null=True)

    def to_internal_value(self, data: "System") -> dict:
        new_data = {
            "ip_address": data.ip_address,
            "hostname": data.hostname if hasattr(data, "hostname") else "unknown",
        }
        return super().to_internal_value(new_data)


class NetworkSerializer(serializers.Serializer):
    cidr = CidrField()
    asset_count = serializers.IntegerField(min_value=0)
    connection_count = serializers.IntegerField(min_value=0)

    def to_internal_value(
        self, data: dict[str, dict[str, int]]
    ) -> dict[str, str | int]:
        new_data = {}
        for cidr in data:
            new_data = {
                "cidr": cidr,
                "asset_count": data[cidr]["asset_count"],
                "connection_count": data[cidr]["connection_count"],
            }
        return super().to_internal_value(new_data)


class TopologyResponseSerializer(serializers.Serializer):
    schema_version = serializers.CharField(default="0.1.0-minimal")
    snapshot_id = serializers.IntegerField(required=True)
    timestamp = serializers.DateTimeField(required=True)
    assets = serializers.ListField(child=AssetResponseSerializer(), allow_empty=True)
    connections = serializers.ListField(
        child=ConnectionResponseSerializer(), allow_empty=True
    )
    external_endpoints = serializers.ListField(
        child=ExternalEndpointsResponseSerializer(), allow_empty=True
    )
    query = QueryResponseSerializer()
    networks = serializers.ListField(child=NetworkSerializer(), allow_empty=True)
