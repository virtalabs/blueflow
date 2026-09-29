import ipaddress
from collections import abc

from django.core import exceptions
from django.db import models
from django.utils.translation import gettext_lazy as _


class Network(models.Model):
    """Model a network and any related subnets.

    Name: the snmp vlan `name` of the network
    cidrs: the list of cidrs/subnets associated with this network
    """

    name = models.CharField(blank=False, null=False, default="NO NAME")

    def __str__(self) -> str:
        return self.name


def to_cidr(value: str) -> ipaddress.IPv4Network:
    try:
        return ipaddress.IPv4Network(value)
    except (ipaddress.AddressValueError, ValueError) as e:
        msg = _("Unable to parse ipv4 cidr due to error")
        raise exceptions.ValidationError(msg) from e


def validate_cidr(value: str) -> None:
    """Validate cidrs in a maner that is mypy compliant."""
    _ = to_cidr(value)


class CidrField(models.CharField):
    """Model the django field for a `cidr` range.

    Blank & null are _always_ false to ensure the str is compliant
    w/ ipaddres.IPv4Network's init func.

    Further, the largest supported range is `255.255.255.255/32` which has 18 chars.
    """

    description = _("Models a valid cidr range")
    default_validators = [validate_cidr]  # noqa: RUF012

    def __init__(self, *args, **kwargs):
        kwargs["blank"] = False
        kwargs["null"] = False
        kwargs["max_length"] = 18
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> tuple[str, str, abc.Sequence, dict]:
        name, path, args, kwargs = super().deconstruct()
        for k in ("blank", "null", "max_length"):
            kwargs.pop(k, None)
        return name, path, args, kwargs

    def get_prep_value(self, value: str | ipaddress.IPv4Network) -> str:
        value = super().get_prep_value(value)
        if isinstance(value, ipaddress.IPv4Network):
            return str(value)
        return str(to_cidr(value))

    def from_db_value(self, value: str | None, *_) -> ipaddress.IPv4Network | None:
        if value is None:
            return value
        return to_cidr(value)

    def to_python(
        self, value: str | ipaddress.IPv4Network, *_
    ) -> ipaddress.IPv4Network:
        if isinstance(value, ipaddress.IPv4Network):
            return value
        return to_cidr(value)


class Cidr(models.Model):
    """Model a cidr range.

    value: the cidr range
    """

    value = CidrField(blank=False, null=False)
    network = models.ForeignKey(Network, related_name="cidrs", on_delete=models.CASCADE)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("value", "network"), name="unique_network_cidr"
            ),
        )

    def __str__(self) -> str:
        return str(self.value)
