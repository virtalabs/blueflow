from datetime import UTC, datetime

from network import models, serializers
from rest_framework import generics, request, response, status


class Topology(generics.ListAPIView):
    def list(self, req: request.Request) -> response.Response:
        """Provide a list containing all assets in a given cidr range.

        The asset data includes ID references which can be crawled
        to build a Graph of the Network Topology.

        Refer to the api yaml for specifics.
        """
        query = req.query_params
        serializer = serializers.TopologyRequestSerializer(data=query)
        serializer.is_valid(raise_exception=True)
        cidrs = serializer.validated_data.get("cidrs", None)
        network = serializer.validated_data.get("network", None)
        scope = serializer.validated_data["scope"]
        querier = models.TopologyQuerier(cidrs, scope)
        assets = querier.assets
        connections = querier.connections
        external_endpoints = querier.external_systems
        networks = querier.networks
        query = {"scope": scope}
        if cidrs is not None:
            query["cidrs"] = cidrs
        if network is not None:
            query["network"] = network
        dirty_response = {
            "schema_version": "0.1.0-minimal",
            "snapshot_id": 1,
            "timestamp": datetime.now(UTC),
            "assets": assets,
            "connections": connections,
            "external_endpoints": external_endpoints,
            "query": query,
            "networks": networks,
        }
        serializer = serializers.TopologyResponseSerializer(data=dirty_response)
        if serializer.is_valid():
            validated_response = serializer.validated_data
            return response.Response(validated_response, status=status.HTTP_200_OK)
        return response.Response(
            serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
