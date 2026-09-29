import pytest
from model_bakery import baker

from blueflow import models, queries


@pytest.fixture
def make_assets():
    def _make_assets(ips: list[str] | None = None) -> list[models.Asset]:
        if ips is None:
            ips = ["127.0.0.1"]
        assets = []
        for ip in ips:
            a = baker.make("Asset")
            baker.make("NetworkInterface", system=a, ipv4=ip)
            assets.append(a)
        return assets

    return _make_assets


@pytest.fixture
def make_request():
    def _make_request(
        *,
        port: int = 80,
        protocol: str = "TCP",
        cast_type: models.Request.CastChoices = models.Request.CastChoices.unicast,
        service: str = "No Service Name",
        response_seen: bool = False,
    ):
        return baker.make(
            "blueflow.Request",
            port=port,
            protocol=protocol,
            cast_type=cast_type,
            service=service,
            response_seen=response_seen,
        )

    return _make_request


@pytest.fixture
def make_system_requests(make_request):
    def _make_system_requests(
        senders: list[models.Asset], receivers: list[models.Asset]
    ) -> list[models.SystemRequest]:
        if len(senders) != len(receivers):
            msg = "Senders and receivers list must be of same length!"
            raise ValueError(msg)
        requests = []
        for i, a1 in enumerate(senders):
            a2 = receivers[i]
            request = make_request()
            system_request = baker.make(
                "blueflow.SystemRequest", sender=a1, receiver=a2, request=request
            )
            requests.append(system_request)
        return requests

    return _make_system_requests


@pytest.fixture
def topology_querier():
    def _querier(cidrs, scope):
        return queries.TopologyQuerier(cidrs, scope)

    return _querier
