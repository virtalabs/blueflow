import csv
import io
import pathlib

from django import db, http
from django.conf import settings
from django.core import management
from rest_framework import exceptions, parsers, request, response, status, views

from blueflow import models, permissions


class CsvView(views.APIView):
    """Controls the endpoints for downloading or uploading csv."""

    permission_classes = (permissions.IsBiomedical | permissions.IsAdmin,)
    parser_classes = (parsers.MultiPartParser,)

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

    def post(self, req: request.Request) -> response.Response:
        if "file" not in req.FILES:
            raise exceptions.ValidationError({"file": "This field is required."})
        text = io.TextIOWrapper(req.FILES["file"], encoding="utf-8", newline="")
        try:
            created, updated = models.Asset.import_rows(csv.DictReader(text))
        except (ValueError, db.IntegrityError) as e:
            raise exceptions.ValidationError(str(e)) from e
        return response.Response(
            {"created": created, "updated": updated}, status=status.HTTP_201_CREATED
        )
