"""Define a suite of tests to ensure authentication is followed on all viewsets."""

import pytest

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
