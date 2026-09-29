import ipaddress
from collections import abc

from django.db.models import Q
from network import constants

from blueflow import models

Cidr = ipaddress.IPv4Network | ipaddress.IPv6Network
Cidrs = abc.Iterable[Cidr]
NetworkCounts = dict[str, int]
Systems = abc.Iterable[models.System]
Connections = abc.Iterable[models.SystemRequest]
Networks = abc.Iterable[dict[Cidr, NetworkCounts]]


class TopologyQuerier:
    def __init__(self, cidrs: Cidrs, scope: constants.ScopeChoices):
        self.cidrs = cidrs
        self.scope = scope
        self._networks: dict[Cidr, NetworkCounts] = {}
        self._assets: Systems = []
        self._connections: Connections = []
        self._external_systems: Systems = []
        self._prefetch_related()
        self._init_query()

    def _prefetch_related(self):
        self._asset_qs = models.Asset.objects.prefetch_related("interface")
        self._system_qs = models.System.objects.prefetch_related("interface")
        self._request_qs = models.SystemRequest.objects.prefetch_related(
            "sender"
        ).prefetch_related("receiver")

    def _init_query(self):
        if not self.cidrs:
            self._query_all()
        else:
            self._query_with_cidr()
        # external systems only need to be calculated when the network
        # edge is requested
        if self.scope == constants.ScopeChoices.internal:
            return
        self._query_external_systems()

    def _query_all(self):
        assets = self._asset_qs.all()
        self._assets = assets
        connections = self._request_qs.all()
        self._connections = connections

    def _query_with_cidr(self):
        all_asset_query = Q()
        all_connections_query = Q()
        for cid in self.cidrs:
            network = self.get_network(cid)
            ### assets
            asset_query = Q(interface__ipv4__net_contained=cid)
            cidr_assets = self._asset_qs.filter(asset_query)
            asset_count = cidr_assets.count()
            network.setdefault("asset_count", asset_count)
            all_asset_query |= asset_query

            ### connections
            connection_query = Q(sender__in=cidr_assets) | Q(receiver__in=cidr_assets)
            con_count = self._request_qs.filter(connection_query).count()
            network.setdefault("connection_count", con_count)
            all_connections_query |= connection_query

        assets = self._asset_qs.filter(all_asset_query)
        self._assets = assets
        connections = self._request_qs.filter(all_connections_query)
        self._connections = connections

    def _query_external_systems(self):
        unique_asset_ips = {a.ip_address for a in self.assets}
        unique_connections = {
            c.sender.interface.ip_address for c in self.connections
        } | {
            c.receiver.interface.ip_address
            for c in self.connections
            if c.receiver is not None
        }
        external_ips = unique_connections - unique_asset_ips
        external_systems = self._system_qs.filter(interface__ipv4__in=external_ips)
        self._external_systems = external_systems

    def get_network(self, cidr: Cidr) -> NetworkCounts:
        return self._networks.setdefault(cidr, {})

    @property
    def assets(self) -> Systems:
        return self._assets

    @property
    def connections(self) -> Connections:
        return self._connections

    @property
    def external_systems(self) -> Systems:
        return self._external_systems

    @property
    def networks(self) -> Networks:
        return [{k: v} for k, v in self._networks.items()]
