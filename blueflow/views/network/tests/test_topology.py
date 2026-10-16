import pytest
from model_bakery import baker
from rest_framework import response, status

from blueflow.models.network import constants

TOPOLOGY_URL = "/api/network/topology/"


def _get_topology_with_query(
    admin_client, key: str, arg: list[str] | str, url: str = TOPOLOGY_URL
) -> response.Response:
    response = admin_client.get(url, {key: arg})
    return response


@pytest.mark.django_db
def test_topology_accepts_cidr_query(admin_client) -> None:
    cidrs = ["198.51.100.0/24"]
    response = _get_topology_with_query(admin_client, "cidrs", cidrs)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "assets" in data
    assert "query" in data


@pytest.mark.django_db
def test_topology_cidr_query_responds_with_assets(admin_client) -> None:
    a = baker.make("blueflow.Asset", hostname="test-mcgee")
    baker.make("blueflow.NetworkInterface", system=a, ipv4="192.51.32.4")
    cidrs = ["192.51.32.0/24"]
    response = _get_topology_with_query(admin_client, "cidrs", cidrs)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "assets" in data
    assert "query" in data
    assets = data["assets"]
    assert len(assets) == 1
    assert assets[0]["id"] == a.id


@pytest.mark.django_db
def test_topology_cidr_list_query_responds_with_assets(admin_client) -> None:
    a = baker.make("blueflow.Asset", hostname="test-mcgee")
    baker.make("blueflow.NetworkInterface", system=a, ipv4="192.51.32.4")
    b = baker.make("blueflow.Asset", hostname="test-mcgee2")
    baker.make("blueflow.NetworkInterface", system=b, ipv4="197.52.33.5")
    cidrs = ["192.51.32.0/24", "197.52.0.0/16"]
    response = _get_topology_with_query(admin_client, "cidrs", cidrs)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "assets" in data
    assert "query" in data
    assets = data["assets"]
    assert len(assets) == 2
    assert assets[0]["id"] == a.id
    assert assets[1]["id"] == b.id


@pytest.mark.django_db
def test_topology_cidr_list_query_responds_with_assets_and_network_rollup(
    admin_client,
) -> None:
    a = baker.make("blueflow.Asset", hostname="test-mcgee")
    baker.make("blueflow.NetworkInterface", system=a, ipv4="192.51.32.4")
    b = baker.make("blueflow.Asset", hostname="test-mcgee2")
    baker.make("blueflow.NetworkInterface", system=b, ipv4="197.52.33.5")
    cidrs = ["192.51.32.0/24", "197.52.0.0/16"]
    response = _get_topology_with_query(admin_client, "cidrs", cidrs)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "assets" in data
    assert "query" in data
    assets = data["assets"]
    assert len(assets) == 2
    assert assets[0]["id"] == a.id
    assert assets[1]["id"] == b.id
    assert "networks" in data
    network_list = data["networks"]
    assert len(network_list) == len(cidrs), (
        "Expected network list to match the length of cidr query"
    )
    for net in network_list:
        assert "cidr" in net
        assert net["cidr"] in cidrs, (
            "Expected network rollup to contain cidrs from cidrs query"
        )
        assert "asset_count" in net
        assert net["asset_count"] == 1
        assert "connection_count" in net
        assert net["connection_count"] == 0


@pytest.mark.django_db
def test_topology_cidr_list_query_responds_with_network_rollup_and_connections(
    admin_client,
    make_assets,
    make_system_requests,
) -> None:
    sender_ips = ["192.23.42.1", "192.23.42.2"]
    senders = make_assets(sender_ips)
    receiver_ips = ["10.11.12.4", "10.11.33.2"]
    receivers = make_assets(receiver_ips)
    make_system_requests(senders, receivers)

    cidrs = ["192.23.0.0/16", "10.11.0.0/16"]
    response = _get_topology_with_query(admin_client, "cidrs", cidrs)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "assets" in data
    assert "query" in data
    assets = data["assets"]
    all_created_assets = senders + receivers
    assert len(assets) == len(all_created_assets)
    all_created_ids = [a.id for a in all_created_assets]
    assert all(a["id"] in all_created_ids for a in assets)
    assert "networks" in data
    network_list = data["networks"]
    assert len(network_list) == len(cidrs), (
        "Expected network list to match the length of cidr query"
    )
    for net in network_list:
        assert "cidr" in net
        assert net["cidr"] in cidrs, (
            "Expected network rollup to contain cidrs from cidrs query"
        )
        assert "asset_count" in net
        assert net["asset_count"] == len(receivers)
        assert "connection_count" in net
        assert net["connection_count"] == len(receivers)


@pytest.mark.django_db
def test_topology_cidr_list_query_responds_with_unique_assets(admin_client) -> None:
    a = baker.make("blueflow.Asset", hostname="test-mcgee")
    baker.make("blueflow.NetworkInterface", system=a, ipv4="192.51.32.4")
    cidrs = ["192.51.32.0/24", "192.51.0.0/16"]
    response = _get_topology_with_query(admin_client, "cidrs", cidrs)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "assets" in data
    assert "query" in data
    assets = data["assets"]
    assert len(assets) == 1
    assert assets[0]["id"] == a.id


@pytest.mark.django_db
def test_topology_accepts_network_query(admin_client) -> None:
    network = "ER"
    response = _get_topology_with_query(admin_client, "network", network)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "query" in data
    assert "network" in data["query"]
    assert network in data["query"]["network"]


@pytest.mark.django_db
def test_topology_accepts_scope_query(admin_client) -> None:
    scope = "boundary"
    response = _get_topology_with_query(admin_client, "scope", scope)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_topology_accepts_empty_query(admin_client) -> None:
    response = admin_client.get(TOPOLOGY_URL)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_topology_response_keys(admin_client) -> None:
    response = admin_client.get(TOPOLOGY_URL)
    assert response.status_code == status.HTTP_200_OK
    required_keys = [
        "schema_version",
        "snapshot_id",
        "timestamp",
        "assets",
        "connections",
        "external_endpoints",
        "query",
        "networks",
    ]
    json = response.json()
    for k in required_keys:
        actual_keys = json.keys()
        assert k in actual_keys, f"{k} is a required field in /topology responses"


@pytest.mark.django_db
def test_topology_response_contains_connections(
    admin_client, make_assets, make_system_requests
):
    sender_ips = ["192.23.42.1", "192.23.42.2"]
    senders = make_assets(sender_ips)
    receiver_ips = ["10.11.12.4", "10.11.33.2"]
    receivers = make_assets(receiver_ips)
    make_system_requests(senders, receivers)

    cidrs = ["192.23.0.0/16", "10.11.0.0/16"]
    response = _get_topology_with_query(admin_client, "cidrs", cidrs)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "connections" in data
    connections = data["connections"]
    assert len(connections) == len(sender_ips), (
        "Connection length must be exactly the same as created senders list"
    )

    found_senders = {c["src_ip"] for c in connections}
    assert set(sender_ips) == found_senders
    found_receivers = {c["dst_ip"] for c in connections}
    assert set(receiver_ips) == found_receivers


@pytest.mark.django_db
def test_topology_response_contains_external(
    admin_client, make_assets, make_system_requests
):
    sender_ips = ["192.23.42.1", "192.23.42.2"]
    senders = make_assets(sender_ips)
    receiver_ips = ["10.11.12.4", "10.11.33.2"]
    receivers = make_assets(receiver_ips)
    make_system_requests(senders, receivers)

    cidrs = ["192.23.0.0/16"]
    response = _get_topology_with_query(admin_client, "cidrs", cidrs)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "connections" in data
    connections = data["connections"]
    assert len(connections) == len(sender_ips), (
        "Connection length must be exactly the same as created senders list"
    )

    found_senders = {c["src_ip"] for c in connections}
    assert set(sender_ips) == found_senders
    found_receivers = {c["dst_ip"] for c in connections}
    assert set(receiver_ips) == found_receivers
    assert "external_endpoints" in data
    external = data["external_endpoints"]
    assert len(external) == len(receivers)
    external_ips = {e["ip_address"] for e in external}
    assert set(receiver_ips) == external_ips


@pytest.mark.django_db
def test_topology_response_scoped_to_boundary_contains_external(
    admin_client, make_assets, make_system_requests
):
    sender_ips = ["192.23.42.1", "192.23.42.2"]
    senders = make_assets(sender_ips)
    receiver_ips = ["10.11.12.4", "10.11.33.2"]
    receivers = make_assets(receiver_ips)
    make_system_requests(senders, receivers)

    cidrs = ["192.23.0.0/16"]
    query = {"cidrs": cidrs, "scope": constants.ScopeChoices.boundary}
    response = admin_client.get(TOPOLOGY_URL, query)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "connections" in data
    connections = data["connections"]
    assert len(connections) == len(sender_ips), (
        "Connection length must be exactly the same as created senders list"
    )

    found_senders = {c["src_ip"] for c in connections}
    assert set(sender_ips) == found_senders
    found_receivers = {c["dst_ip"] for c in connections}
    assert set(receiver_ips) == found_receivers
    assert "external_endpoints" in data
    external = data["external_endpoints"]
    assert len(external) == len(receivers)
    external_ips = {e["ip_address"] for e in external}
    assert set(receiver_ips) == external_ips


@pytest.mark.django_db
def test_topology_response_scoped_to_internal_does_not_contain_external(
    admin_client, make_assets, make_system_requests
):
    sender_ips = ["192.23.42.1", "192.23.42.2"]
    senders = make_assets(sender_ips)
    receiver_ips = ["10.11.12.4", "10.11.33.2"]
    receivers = make_assets(receiver_ips)
    make_system_requests(senders, receivers)

    cidrs = ["192.23.0.0/16"]
    query = {"cidrs": cidrs, "scope": constants.ScopeChoices.internal}
    response = admin_client.get(TOPOLOGY_URL, query)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "connections" in data
    connections = data["connections"]
    assert len(connections) == len(sender_ips), (
        "Connection length must be exactly the same as created senders list"
    )

    found_senders = {c["src_ip"] for c in connections}
    assert set(sender_ips) == found_senders
    found_receivers = {c["dst_ip"] for c in connections}
    assert set(receiver_ips) == found_receivers
    assert "external_endpoints" in data
    external = data["external_endpoints"]
    assert len(external) == 0
