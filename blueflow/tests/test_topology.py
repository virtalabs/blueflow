import pytest
from django import urls
from rest_framework import status

INVALID_CIDRS = ["garbage", "10.0.0.0/33", "300.0.0.0/24", "10.0.0.1/24", "", "::/129"]
VALID_CIDRS = ["10.0.0.0/24", "192.168.1.0/24", "10.0.0.5/32", "fd00::/64"]


@pytest.fixture
def url():
    return urls.reverse("blueflow:topology")


@pytest.mark.parametrize("cidr", INVALID_CIDRS)
def test_invalid_cidr_rejected(auth_client, url, cidr):
    resp = auth_client.get(url, {"cidrs": cidr})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "cidrs" in resp.json()


@pytest.mark.parametrize("cidr", VALID_CIDRS)
def test_valid_cidr_accepted(auth_client, url, cidr):
    resp = auth_client.get(url, {"cidrs": cidr})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["query"]["cidrs"] == [cidr]


def test_one_bad_cidr_rejects_request(auth_client, url):
    resp = auth_client.get(url, {"cidrs": ["10.0.0.0/24", "nope"]})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
