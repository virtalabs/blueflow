"""Asset is the core model for tracking all internal systems."""

import dataclasses
import datetime
import json
import logging
import typing
from collections import abc

import netaddr
from django.apps import apps
from django.core import exceptions
from django.core.management import color
from django.db import connection, models, transaction
from simple_history import models as simple_history

from blueflow.models import (
    cpe,
    group,
    request,
    tag,
    usage,
)

from . import system, util

logger = logging.getLogger(__name__)


class Asset(system.System):
    """Asset represents any system internal to the owned network.

    Asset instances are intended to be queried and managed by its parent:
    ex:
    s = System.objects.first()
    asset = getattr(s, "asset", None)

    Inherits ``created`` and ``modified`` from ``TimeStampedModel``. ``modified``
    is the sync anchor used by the Viper webhook — it updates on every save,
    including upserts. ``last_pinged`` is reserved for the network
    layer and is only set when the asset is observed on the wire (ping,
    fingerprint), so it is not safe to use as a "recently changed" filter.
    """

    UNKNOWN_OUI_MANUFACTURER: str = ""

    name = models.CharField(
        max_length=126,
        blank=True,
        null=False,
        default="",
    )
    # we want nullable for uniqueness
    hostname = models.CharField(  # noqa: DJ001
        max_length=256,
        blank=False,
        null=True,
        unique=True,
    )
    oui_manufacturer = models.CharField(
        max_length=256,
        blank=True,
        null=False,
        verbose_name="NIC vendor",
        default="",
    )
    manufacturer = models.CharField(
        max_length=256,
        blank=True,
        null=False,
        default="",
    )
    model = models.CharField(
        max_length=256,
        blank=True,
        null=False,
        default="",
    )
    serial_number = models.CharField(
        max_length=256,
        blank=True,
        null=False,
        default="",
    )
    udi = models.CharField(
        max_length=256,
        blank=True,
        null=False,
        verbose_name="UDI",
        default="",
    )
    tag_number = models.CharField(
        max_length=256,
        blank=True,
        null=False,
        default="",
    )
    category = models.CharField(
        max_length=256,
        blank=True,
        null=False,
        default="",
    )
    owner = models.CharField(max_length=256, blank=True, null=False, default="")
    os = models.CharField(
        max_length=256,
        blank=True,
        null=False,
        verbose_name="Operating System",
        default="",
    )
    app_sw_version = models.CharField(
        max_length=256,
        blank=True,
        null=False,
        verbose_name="Application software version",
        default="",
    )
    last_scanned = models.DateTimeField(
        null=False,
        default=util.default_timestamp,
    )
    last_pinged = models.DateTimeField(
        null=False,
        default=util.default_timestamp,
    )
    external_keys = models.JSONField(
        blank=True,
        null=True,
    )
    groups = models.ManyToManyField(
        group.Group,
        through=group.AssetGroup,
    )
    tags = models.ManyToManyField(
        tag.Tag,
        through=tag.AssetTag,
    )
    history = simple_history.HistoricalRecords()

    class Meta:
        constraints: typing.ClassVar = (
            models.CheckConstraint(
                condition=models.Q(hostname__isnull=True) | ~models.Q(hostname=""),
                name="asset_hostname_not_empty_when_set",
            ),
        )

    @classmethod
    def formatter(cls, anything: typing.Any) -> str:
        match anything:
            case datetime.datetime():
                return anything.isoformat()
            case models.Model():
                return str(anything.pk)
            case dict():
                return json.dumps(anything)
            # alternatively we could only conert to json
            # if any subelement is a dict, this seems easier.
            case list():
                return json.dumps(anything)
            case None:
                return ""
            case _:
                return str(anything)

    @classmethod
    def _fields(
        cls, a: "Asset", headers: abc.Iterable[str], formatter=None
    ) -> abc.Iterable[typing.Any]:
        if not formatter:
            formatter = cls.formatter
        for h in headers:
            try:
                attr = getattr(a, h, None)
                yield formatter(attr)
            except exceptions.ObjectDoesNotExist:
                yield None

    @classmethod
    def export_headers(cls) -> abc.Iterable[str]:
        Asset = apps.get_model(app_label="blueflow", model_name="Asset")
        for f in Asset._meta.concrete_fields:  # noqa: SLF001
            _f = str(f.attname)
            yield _f

    @classmethod
    def export(cls) -> abc.Iterable[abc.Iterable[typing.Any]]:
        raw_assets = Asset.objects.all()
        headers = list(cls.export_headers())
        for asset in raw_assets:
            a = cls._fields(asset, headers)
            yield list(a)

    @dataclasses.dataclass
    class ImportRow:
        """Writable columns of an exported csv row; ``None`` leaves a field unset."""

        id: str | None = None
        name: str | None = None
        hostname: str | None = None
        oui_manufacturer: str | None = None
        manufacturer: str | None = None
        model: str | None = None
        serial_number: str | None = None
        udi: str | None = None
        tag_number: str | None = None
        category: str | None = None
        owner: str | None = None
        os: str | None = None
        app_sw_version: str | None = None
        last_scanned: str | None = None
        last_pinged: str | None = None
        external_keys: dict[str, str] | None = None

        @classmethod
        def from_csv(cls, row: dict[str, str]) -> typing.Self:
            names = {f.name for f in dataclasses.fields(cls)} - {"external_keys"}
            values = {k: v for k, v in row.items() if k in names and v != ""}
            external_keys = row.get("external_keys")
            return cls(
                **values,
                external_keys=json.loads(external_keys) if external_keys else None,
            )

        def defaults(self) -> dict[str, typing.Any]:
            """Model kwargs; a blank hostname is always written to clear it."""
            fields = {
                k: v for k, v in dataclasses.asdict(self).items() if v is not None
            }
            fields.pop("id", None)
            fields["hostname"] = self.hostname
            return fields

    @classmethod
    def import_rows(cls, rows: abc.Iterable[dict[str, str]]) -> tuple[int, int]:
        """Create or update assets from exported csv rows, matched on ``id``.

        Inverse of ``export``; returns ``(created, updated)`` counts.
        """
        created = 0
        updated = 0
        with transaction.atomic():
            for raw in rows:
                row = cls.ImportRow.from_csv(raw)
                if row.id is None:
                    Asset.objects.create(**row.defaults())
                    is_new = True
                else:
                    _, is_new = Asset.objects.update_or_create(
                        id=row.id, defaults=row.defaults()
                    )
                created += is_new
                updated += not is_new
            # Explicit ids don't advance the pk sequence; resync it like loaddata.
            parents = cls._meta.get_parent_list()
            with connection.cursor() as cursor:
                for sql in connection.ops.sequence_reset_sql(color.no_style(), parents):
                    cursor.execute(sql)
        return created, updated

    @property
    def cpe(self) -> str:
        """Build this asset's CPE 2.3 string from manufacturer / model.

        Delegates to :func:`blueflow.models.cpe.build_cpe` so the CPE format is
        defined in one place; most slots are still stubbed pending real data.
        """
        return cpe.build_cpe(self)

    @dataclasses.dataclass
    class Service:
        name: str
        protocols: list[str]

    def _get_request_services(self, request_type: abc.Iterable) -> dict[int, Service]:
        services: dict[int, Asset.Service] = {}
        for r in request_type:
            port = int(r.request.port)
            protocol = str(r.request.protocol)
            name = str(r.request.service)
            s = services.setdefault(port, self.Service(name="", protocols=[]))
            if protocol not in s.protocols:
                s.protocols.append(protocol)
            s.name = name
            services[port] = s
        return services

    @property
    def services(self) -> dict[int, Service]:
        """A list of services associated with this asset.

        Assumes prefetched as needed
        """
        return self._get_request_services(
            [*self.request_receivers.all(), *self.request_senders.all()]
        )

    def __str__(self) -> str:
        return f"{self.id}:{self.hostname}:{self.ip_address}"

    def add_service(self, port: int, protocol: str) -> bool:
        """Idempotently link this asset to a ``(port, protocol)`` observation.

        The shared ``Request`` lookup row is created on first use; the
        per-asset through row is created on first reference. Returns True if a
        new link was created, False if it already existed.
        """
        r, _ = request.Request.objects.get_or_create(port=port, protocol=protocol)
        _, created = request.SystemRequest.objects.get_or_create(sender=self, request=r)
        return created

    def add_or_update_interface(self, **kwargs):
        interface = super().add_or_update_interface(**kwargs)
        if not interface.mac_address:
            return interface
        mac = interface.mac_address
        try:
            reg = mac.oui.registration()
            self.oui_manufacturer = reg.org.strip()
            self.save()
            # assert 0
        except netaddr.core.AddrFormatError:
            logger.warning("Bad MAC address on asset %s", self)
            self.oui_manufacturer = self.UNKNOWN_OUI_MANUFACTURER
        except netaddr.core.NotRegisteredError:
            logger.info(
                "MAC address %s of asset %s lacks NIC vendor",
                mac,
                self,
            )
            self.oui_manufacturer = self.UNKNOWN_OUI_MANUFACTURER
        except AttributeError:
            logger.debug(
                "NIC vendor registry lacks org detail for MAC address %s",
                mac,
            )
            self.oui_manufacturer = self.UNKNOWN_OUI_MANUFACTURER
        return interface

    def update_usage(self, timestamp: datetime.datetime) -> None:
        """Record a usage observation for this asset at the given timestamp.

        Looks up (or creates) the Usage row for this asset on
        timestamp.weekday(), then increments the matching hour_NN column —
        unless an observation has already been counted for the same
        Usage.USAGE_WINDOW_MINUTES window, in which case this is a no-op.
        """
        window_start = usage.Usage.floor_to_window(timestamp)
        u, _ = usage.Usage.objects.get_or_create(
            asset=self,
            day_of_week=timestamp.weekday(),
        )
        if u.last_window_started_at == window_start:
            return
        hour_field = f"hour_{timestamp.hour:02d}"
        setattr(u, hour_field, getattr(u, hour_field) + 1)
        u.last_window_started_at = window_start
        u.save()

    def todict(self) -> dict[str, str]:
        """Return concrete fields as a dictionary for diffing in update_or_create."""
        return {f.name: str(getattr(self, f.attname, None)) for f in self._meta.fields}
