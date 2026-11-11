"""Tests for the csv export and import view."""

import csv
import io

import pytest
from django import urls
from django.core import management
from django.core.files.uploadedfile import SimpleUploadedFile
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from blueflow import models, permissions
from blueflow.tests import factories


def url() -> str:
    return urls.reverse("blueflow:csv")


@pytest.fixture(autouse=True)
def _export_path(settings, tmp_path):
    # The view writes to a fixed path; isolate it per test for xdist.
    settings.DEFAULT_EXPORT_PATH = str(tmp_path / "view.csv")


def role_client(make=None) -> APIClient:
    # Non-superuser on purpose: superusers bypass every IsPermission check.
    user = factories.make_user()
    if make:
        make(user)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def body(response) -> bytes:
    # The test client closes the response (and the file) once the stream is
    # exhausted; calling response.close() directly would drop the DB connection.
    return b"".join(response.streaming_content)


def rows(response) -> list[dict[str, str]]:
    text = body(response).decode("utf-8")
    return list(csv.DictReader(io.StringIO(text, newline=""), strict=True))


def test_biomedical_can_get():
    response = role_client(permissions.IsBiomedical.make).get(url())
    assert response.status_code == status.HTTP_200_OK
    assert response["content-type"] == "text/csv"
    body(response)


def test_admin_can_get():
    response = role_client(permissions.IsAdmin.make).get(url())
    assert response.status_code == status.HTTP_200_OK
    body(response)


@pytest.mark.parametrize(
    "make", [permissions.IsViewer.make, None], ids=["viewer", "no_role"]
)
def test_other_roles_forbidden(make):
    response = role_client(make).get(url())
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_unauthenticated_rejected():
    response = APIClient().get(url())
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_csv_matches_db():
    baker.make("Asset", name="alpha", hostname="alpha.local", os="Linux")
    baker.make("Asset", name="beta", hostname="beta.local", os="Windows")
    response = role_client(permissions.IsBiomedical.make).get(url())
    by_id = {row["id"]: row for row in rows(response)}

    assets = models.Asset.objects.all()
    assert set(by_id) == {str(a.pk) for a in assets}
    for asset in assets:
        row = by_id[str(asset.pk)]
        assert row["name"] == asset.name
        assert row["hostname"] == asset.hostname
        assert row["os"] == asset.os


def test_csv_matches_command_output(tmp_path):
    baker.make("Asset", _quantity=3)
    response = role_client(permissions.IsBiomedical.make).get(url())
    path = tmp_path / "cmd.csv"
    management.call_command("export_assets", filepath=str(path))
    assert body(response) == path.read_bytes()


def upload(client: APIClient, text: str):
    file = SimpleUploadedFile("assets.csv", text.encode(), content_type="text/csv")
    return client.post(url(), {"file": file}, format="multipart")


@pytest.mark.parametrize(
    "make",
    [permissions.IsBiomedical.make, permissions.IsAdmin.make],
    ids=["biomedical", "admin"],
)
def test_allowed_roles_can_post(make):
    response = upload(role_client(make), "name\nalpha\n")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"created": 1, "updated": 0}


@pytest.mark.parametrize(
    "make", [permissions.IsViewer.make, None], ids=["viewer", "no_role"]
)
def test_post_other_roles_forbidden(make):
    response = upload(role_client(make), "name\nalpha\n")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not models.Asset.objects.exists()


def test_post_unauthenticated_rejected():
    response = upload(APIClient(), "name\nalpha\n")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_post_creates_and_updates():
    asset = baker.make("Asset", name="old")
    text = f"id,name\n{asset.id},new\n,fresh\n"
    response = upload(role_client(permissions.IsBiomedical.make), text)
    assert response.json() == {"created": 1, "updated": 1}
    asset.refresh_from_db()
    assert asset.name == "new"
    assert models.Asset.objects.filter(name="fresh").exists()


def test_post_round_trip_from_get():
    baker.make("Asset", _quantity=3)
    client = role_client(permissions.IsBiomedical.make)
    exported = body(client.get(url())).decode("utf-8")
    response = upload(client, exported)
    assert response.json() == {"created": 0, "updated": 3}
    assert models.Asset.objects.count() == 3
    assert body(client.get(url())).decode("utf-8").count("\n") == exported.count("\n")


def test_post_utf8_and_quoted_newlines():
    name = 'Ünïcode, "q"\nline2'
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerows([["name"], [name]])
    upload(role_client(permissions.IsBiomedical.make), buf.getvalue())
    assert models.Asset.objects.get().name == name


def test_post_rejects_json_body():
    client = role_client(permissions.IsBiomedical.make)
    response = client.post(url(), {}, format="json")
    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


def test_post_missing_file_is_bad_request():
    client = role_client(permissions.IsBiomedical.make)
    response = client.post(url(), {}, format="multipart")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_malformed_external_keys_is_bad_request():
    text = 'name,external_keys\nalpha,"{not json"\n'
    response = upload(role_client(permissions.IsBiomedical.make), text)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_duplicate_hostname_is_bad_request():
    baker.make("Asset", hostname="taken")
    response = upload(role_client(permissions.IsBiomedical.make), "hostname\ntaken\n")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
