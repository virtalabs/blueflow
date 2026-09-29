from rest_framework import serializers

from blueflow.models import constants


class TelemetryRequestSerializer(serializers.Serializer):
    src_ip = serializers.IPAddressField(protocol="ipv4")
    dst_ip = serializers.IPAddressField(protocol="ipv4")
    dst_port = serializers.IntegerField(
        min_value=constants.PORT_MIN, max_value=constants.PORT_MAX
    )
    protocol = serializers.CharField()
    service = serializers.CharField()
    response_observed = serializers.BooleanField()
