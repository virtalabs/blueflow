import pathlib

from django import http
from django.conf import settings
from django.core import management
from rest_framework import request, status, views

from blueflow import permissions


class CsvView(views.APIView):
    """Controls the endpoints for downloading or uploading csv."""

    permission_classes = (permissions.IsBiomedical | permissions.IsAdmin,)

    def get(self, _: request.Request) -> http.FileResponse:
        path = settings.DEFAULT_EXPORT_PATH
        management.call_command("export_assets", filepath=path)
        # django wants to manage the file io for us
        file = pathlib.Path(path).open(mode="rb")  # noqa: SIM115
        headers = {
            "content-type": "text/csv",
        }
        return http.FileResponse(
            file, as_attachment=True, headers=headers, status=status.HTTP_200_OK
        )
