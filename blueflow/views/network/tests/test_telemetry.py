import pytest
from rest_framework import status

from blueflow import models

TELEMETRY_URL = "/network/telemetry/"


@pytest.mark.django_db
def test_telemtry_post_accepts_sample_payload(client) -> None:
    payload = {
        "src_ip": "10.10.0.1",
        "dst_ip": "10.10.0.2",
        "dst_port": 22,
        "protocol": "tcp",
        "service": "ssh",
        "response_observed": True,
        "visibility": "full",
        "provenance": "zeek",
        "first_seen": "2026-08-13T18:04:51.971005Z",
        "last_seen": "2026-08-13T18:04:51.987003Z",
        "evidence": {
            "conn_state": "SF",
            "history": "ShADadFf",
            "orig_bytes": 23,
            "resp_bytes": 30,
            "orig_pkts": 6,
            "resp_pkts": 4,
            "duration": 0.015998125076293945,
            "missed_bytes": 0,
        },
    }
    response = client.post(TELEMETRY_URL, payload)
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_telemtry_post_creates_system_request(client) -> None:
    payload = {
        "src_ip": "10.10.0.1",
        "dst_ip": "10.10.0.2",
        "dst_port": 22,
        "protocol": "tcp",
        "service": "ssh",
        "response_observed": True,
        "visibility": "full",
        "provenance": "zeek",
        "first_seen": "2026-08-13T18:04:51.971005Z",
        "last_seen": "2026-08-13T18:04:51.987003Z",
        "evidence": {
            "conn_state": "SF",
            "history": "ShADadFf",
            "orig_bytes": 23,
            "resp_bytes": 30,
            "orig_pkts": 6,
            "resp_pkts": 4,
            "duration": 0.015998125076293945,
            "missed_bytes": 0,
        },
    }
    response = client.post(TELEMETRY_URL, payload)
    assert response.status_code == status.HTTP_201_CREATED
    # will error on failed find
    sender = models.System.objects.get(interface__ipv4=payload["src_ip"])
    receiver = models.System.objects.get(interface__ipv4=payload["dst_ip"])
    models.Request.objects.get(
        system_requests__sender=sender,
        system_requests__receiver=receiver,
        port=payload["dst_port"],
        service=payload["service"],
        response_seen=payload["response_observed"],
    )
