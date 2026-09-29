import pytest

from blueflow import models


@pytest.mark.django_db
def test_connection_query_allows_null(make_assets, make_system_requests):
    senders = make_assets(["192.23.42.1", "192.23.42.2"])
    receivers = [None, None]
    make_system_requests(senders, receivers)
    assert models.SystemRequest.objects.count() == 2
    assert models.Request.objects.count() == 2
    assert models.SystemRequest.objects.get(sender=senders[0]).receiver is None
    assert models.SystemRequest.objects.get(sender=senders[1]).receiver is None


@pytest.mark.django_db
def test_connection_query_connects_assets(make_assets, make_system_requests):
    senders = make_assets(["192.23.42.1", "192.23.42.2"])
    receivers = make_assets(["10.11.12.4", "10.14.33.2"])
    make_system_requests(senders, receivers)
    assert models.SystemRequest.objects.count() == 2
    assert models.Request.objects.count() == 2
    assert (
        models.SystemRequest.objects.get(sender=senders[0]).receiver.id
        == receivers[0].id
    )
    assert (
        models.SystemRequest.objects.get(sender=senders[1]).receiver.id
        == receivers[1].id
    )
