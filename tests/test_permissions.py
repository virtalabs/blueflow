"""Tests for the Viewer, Biomedical, and Admin group permissions."""

import pytest
from django import urls
from rest_framework import status
from rest_framework.test import APIClient

from blueflow import permissions
from blueflow.tests import factories
from blueflow.urls import router

MISSING_PK = 999999
DENIED = (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def _cases():
    """Yield (method, url) for every routed action, plus the non-router views."""
    for u in router.urls:
        pattern = str(u.pattern)
        actions = getattr(u.callback, "actions", None)
        if not actions or "format" in pattern:
            continue
        kwargs = {"pk": MISSING_PK} if "<pk>" in pattern else None
        url = urls.reverse(f"blueflow:{u.name}", kwargs=kwargs)
        for method in actions:
            yield method, url
    yield "get", urls.reverse("blueflow:topology")
    yield "post", urls.reverse("blueflow:telemetry")


CASES = list(_cases())
GET_CASES = [c for c in CASES if c[0] == "get"]
WRITE_CASES = [c for c in CASES if c[0] != "get"]
BIOMED_WRITE_CASES = [c for c in WRITE_CASES if c[0] in {"post", "put", "delete"}]
PATCH_CASES = [c for c in WRITE_CASES if c[0] == "patch"]
ADMIN_CASES = [c for c in CASES if c[0] != "patch"]


@pytest.fixture
def biomedical_client(db):
    user = factories.make_user()
    permissions.IsBiomedical.make_biomedical(user)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.parametrize("make", [factories.make_user, factories.make_superuser])
def test_new_user_is_viewer(make):
    user = make()
    assert user.groups.filter(name=permissions.IsViewer.key).exists()


@pytest.mark.parametrize(("method", "url"), GET_CASES)
def test_viewer_can_get(auth_client, method, url):
    response = getattr(auth_client, method)(url)
    assert response.status_code not in DENIED
    assert response.status_code < status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.parametrize(("method", "url"), WRITE_CASES)
def test_viewer_cannot_write(auth_client, method, url):
    response = getattr(auth_client, method)(url, {}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(("method", "url"), CASES)
def test_superuser_bypasses_viewer(method, url):
    user = factories.make_superuser()
    user.groups.clear()
    client = APIClient()
    client.force_authenticate(user=user)
    response = getattr(client, method)(url, {}, format="json")
    assert response.status_code not in DENIED


@pytest.mark.parametrize(("method", "url"), GET_CASES)
def test_biomedical_can_get(biomedical_client, method, url):
    response = getattr(biomedical_client, method)(url)
    assert response.status_code not in DENIED
    assert response.status_code < status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.parametrize(("method", "url"), BIOMED_WRITE_CASES)
def test_biomedical_can_write(biomedical_client, method, url):
    response = getattr(biomedical_client, method)(url, {}, format="json")
    assert response.status_code not in DENIED


@pytest.mark.parametrize(("method", "url"), PATCH_CASES)
def test_biomedical_cannot_patch(biomedical_client, method, url):
    response = getattr(biomedical_client, method)(url, {}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.fixture
def admin_role_client(db):
    user = factories.make_user()
    user.groups.clear()
    permissions.IsAdmin.make(user)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.parametrize(("method", "url"), ADMIN_CASES)
def test_admin_can_do_anything(admin_role_client, method, url):
    response = getattr(admin_role_client, method)(url, {}, format="json")
    assert response.status_code not in DENIED


@pytest.mark.parametrize("url", sorted({url for _, url in CASES}))
def test_admin_can_head(admin_role_client, url):
    response = admin_role_client.head(url)
    assert response.status_code not in DENIED
