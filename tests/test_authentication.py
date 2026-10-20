"""Define a suite of tests to ensure authentication is followed on all viewsets."""

import pytest
from rest_framework.authtoken import models as rf_models

from blueflow.tests import factories

ROUTER_PREFIXES = (
    "assets",
    "assetgroups",
    "assettags",
    "groups",
    "tags",
    "users",
    "crontabs",
    "intervals",
    "periodictask",
)

ENDPOINTS = [
    *(
        (method, f"/api/{prefix}/")
        for prefix in ROUTER_PREFIXES
        for method in ("get", "post")
    ),
    *(
        (method, f"/api/{prefix}/1/")
        for prefix in ROUTER_PREFIXES
        for method in ("get", "put", "patch", "delete")
    ),
    ("patch", "/api/assets/bulk_update/"),
    ("put", "/api/assets/upsert/"),
    ("post", "/api/groups/1/assets/"),
    ("post", "/api/tags/1/assets/"),
    ("post", "/api/viper/webhook/"),
    ("get", "/api/network/topology/"),
    ("post", "/api/network/telemetry/"),
]

IDS = [f"{method.upper()} {path}" for method, path in ENDPOINTS]


@pytest.mark.parametrize(("method", "path"), ENDPOINTS, ids=IDS)
def test_unauthenticated_returns_401(client, method, path):
    """Anonymous requests must be rejected with 401."""
    response = getattr(client, method)(path, content_type="application/json")
    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path"), ENDPOINTS, ids=IDS)
def test_authenticated_not_401(client, method, path):
    """Authenticated requests must get past authentication."""
    client.force_login(factories.make_user())
    response = getattr(client, method)(path, content_type="application/json")
    assert response.status_code != 401


LOGIN_URL = "/api/auth/login/"


def _login(client, **payload):
    return client.post(LOGIN_URL, payload, content_type="application/json")


def test_login_user_returns_token(client):
    """A regular user receives their auth token."""
    user = factories.make_user()
    response = _login(client, username="testuser", password="testpass")
    assert response.status_code == 200
    assert response.json() == {"token": rf_models.Token.objects.get(user=user).key}


def test_login_superuser_returns_token(client):
    """A superuser receives their auth token."""
    user = factories.make_superuser()
    response = _login(client, username="admin", password="adminpass")
    assert response.status_code == 200
    assert response.json() == {"token": rf_models.Token.objects.get(user=user).key}


def test_login_wrong_password_returns_401(client):
    """A bad password is rejected."""
    factories.make_user()
    response = _login(client, username="testuser", password="wrongpass")
    assert response.status_code == 401


def test_login_inactive_user_returns_401(client):
    """Inactive users cannot authenticate even with the right password."""
    factories.make_user(is_active=False)
    response = _login(client, username="testuser", password="testpass")
    assert response.status_code == 401


def test_login_unknown_user_returns_404(client):
    """A username with no matching user is not found."""
    response = _login(client, username="nobody", password="testpass")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"username": "testuser"},
        {"username": "", "password": "testpass"},
        {"username": "abc", "password": "testpass"},
        {"username": "testuser", "password": "abc"},
    ],
    ids=[
        "empty",
        "missing-password",
        "blank-username",
        "short-username",
        "short-password",
    ],
)
def test_login_invalid_payload_returns_400(client, payload):
    """Payloads failing serializer validation are rejected."""
    response = _login(client, **payload)
    assert response.status_code == 400
