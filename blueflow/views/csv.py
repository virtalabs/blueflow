from rest_framework import request, response, serializers, views

from blueflow import permissions


class CsvSerializer(serializers.Serializer): ...


class CsvView(views.APIView):
    """Controls the endpoints for downloading or uploading csv."""

    permission_classes = (permissions.IsBiomedical | permissions.IsAdmin,)

    def get(self, request: request.Request) -> response.Response:
        pass
