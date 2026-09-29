from ipaddress import ip_network

import pytest

from blueflow.models.network import constants


@pytest.mark.django_db
def test_asset_query_out_of_range(make_assets, topology_querier):
    ips = [
        "10.1.1.1",
        "10.1.1.2",
        "10.1.1.3",
    ]
    make_assets(ips)
    query = [ip_network("10.2.2.0/24")]
    querier = topology_querier(query, constants.ScopeChoices.boundary)
    assets = querier.assets
    assert len(assets) == 0, (
        f"Expected to find no asset but instead found: {len(assets)}"
    )


@pytest.mark.django_db
def test_asset_query_in_range(make_assets, topology_querier):
    ips = [
        "10.2.2.1",
        "10.2.2.2",
        "10.2.2.3",
    ]
    make_assets(ips)
    query = [ip_network("10.2.2.0/24")]
    querier = topology_querier(query, constants.ScopeChoices.boundary)
    assets = querier.assets
    assert len(assets) == len(ips), (
        f"Expected to find {len(ips)} assets but instead found: {len(assets)}"
    )
