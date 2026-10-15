from django.db import transaction
from django.forms import model_to_dict
from rest_framework import generics, permissions, request, response, status

from blueflow import models, serializers
from blueflow import permissions as bf_permissions


class Telemetry(generics.GenericAPIView):
    """Telemtry manages all endpoints related to collecting network telemetry data."""

    permission_classes = (permissions.IsAuthenticated, bf_permissions.IsViewer)

    @transaction.atomic
    def post(self, request: request.Request) -> response.Response:
        req_serializer = serializers.TelemetryRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        validated_data = req_serializer.validated_data
        source, created = models.System.objects.get_or_create(
            interface__ipv4=validated_data["src_ip"]
        )
        if created:
            models.NetworkInterface.objects.create(
                ipv4=validated_data["src_ip"], system=source
            )
        destination, created = models.System.objects.get_or_create(
            interface__ipv4=validated_data["dst_ip"]
        )
        if created:
            models.NetworkInterface.objects.create(
                ipv4=validated_data["dst_ip"], system=destination
            )
        tracked_request = models.Request.objects.create(
            port=validated_data["dst_port"],
            protocol=validated_data["protocol"],
            service=validated_data["service"],
            response_seen=validated_data["response_observed"],
        )
        system_request = models.SystemRequest.objects.create(
            sender=source, receiver=destination, request=tracked_request
        )
        return response.Response(
            status=status.HTTP_201_CREATED, data=model_to_dict(system_request)
        )
