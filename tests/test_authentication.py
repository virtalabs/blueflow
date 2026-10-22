"""Define a suite of tests to ensure authentication is followed on all viewsets."""

import pytest
from django.contrib import auth
from rest_framework.authtoken import models as rf_models

from blueflow import permissions
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


REGISTER_URL = "/api/auth/register/"
VIEWER = permissions.IsViewer.key


def _register(client, **payload):
    return client.post(REGISTER_URL, payload, content_type="application/json")


def _groups(user):
    return set(user.groups.values_list("name", flat=True))


def _newuser_exists():
    return auth.get_user_model().objects.filter(username="newuser").exists()


@pytest.fixture
def registrar(client):
    """Client logged in as a group-based (non-superuser) admin."""
    user = factories.make_user(username="registrar")
    permissions.IsAdmin.make_admin(user)
    client.force_login(user)
    return client


def test_register_anonymous_returns_401(client):
    """Anonymous requests cannot register users."""
    response = _register(client, username="newuser", password="newpass")
    assert response.status_code == 401
    assert not _newuser_exists()


@pytest.mark.parametrize(
    "make_role",
    [
        lambda _: None,
        permissions.IsViewer.make_viewer,
        permissions.IsBiomedical.make_biomedical,
    ],
    ids=["no-role", "viewer", "bio"],
)
def test_register_non_admin_returns_403(client, make_role):
    """Authenticated users without the admin role cannot register users."""
    user = factories.make_user()
    make_role(user)
    client.force_login(user)
    response = _register(client, username="newuser", password="newpass")
    assert response.status_code == 403
    assert not _newuser_exists()


def test_register_superuser_allowed(client):
    """Superusers bypass the group check and may register users."""
    client.force_login(factories.make_superuser())
    response = _register(client, username="newuser", password="newpass")
    assert response.status_code == 200
    assert _newuser_exists()


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("viewer", {VIEWER}),
        ("bio", {VIEWER, permissions.IsBiomedical.key}),
        ("admin", {VIEWER, permissions.IsAdmin.key}),
    ],
)
def test_register_role_assigns_groups(registrar, role, expected):
    """Each role lands the new user in the matching group and returns a token."""
    response = _register(registrar, username="newuser", password="newpass", role=role)
    assert response.status_code == 200
    user = auth.get_user_model().objects.get(username="newuser")
    assert response.json() == {"token": rf_models.Token.objects.get(user=user).key}
    assert _groups(user) == expected


def test_register_default_role_is_viewer(registrar):
    """Omitting the role registers a viewer."""
    response = _register(registrar, username="newuser", password="newpass")
    assert response.status_code == 200
    assert _groups(auth.get_user_model().objects.get(username="newuser")) == {VIEWER}


def test_register_password_allows_login(registrar):
    """The registered password is persisted and usable for login."""
    registered = _register(registrar, username="newuser", password="newpass")
    response = _login(registrar, username="newuser", password="newpass")
    assert response.status_code == 200
    assert response.json() == registered.json()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"username": "newuser"},
        {"username": "", "password": "newpass"},
        {"username": "abc", "password": "newpass"},
        {"username": "newuser", "password": "abc"},
        {"username": "newuser", "password": "newpass", "role": "superuser"},
    ],
    ids=[
        "empty",
        "missing-password",
        "blank-username",
        "short-username",
        "short-password",
        "unknown-role",
    ],
)
def test_register_invalid_payload_returns_400(registrar, payload):
    """Payloads failing serializer validation are rejected and create no user."""
    response = _register(registrar, **payload)
    assert response.status_code == 400
    assert not _newuser_exists()


def test_register_duplicate_username_returns_400(registrar):
    """An already-taken username is rejected and the existing user is untouched."""
    factories.make_user(username="newuser")
    response = _register(registrar, username="newuser", password="otherpass")
    assert response.status_code == 400
    assert "username" in response.json()
    assert auth.get_user_model().objects.filter(username="newuser").count() == 1
