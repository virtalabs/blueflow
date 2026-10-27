import csv
import datetime
import pathlib
import typing
from collections import abc

from django.apps import apps
from django.core import exceptions
from django.core.management import base
from django.db import models

from blueflow import models as bf_models

Assets = abc.Iterable[bf_models.Asset]
CollectedAssets = dict[str, Assets | abc.Generator[str]]


DEFAULT_EXPORT = "/tmp/assets.csv"  # noqa: S108 # nosec


def allowed(asset: bf_models.Asset, attr: str) -> bool:
    bad = ["objects", "_meta", "_state", "asset"]
    if attr in bad:
        return False
    if "__" in attr:
        return False
    if not attr.islower():
        return False
    is_callable = callable(getattr(asset, attr, None))
    return not is_callable


def formatter(anything: typing.Any) -> str:
    match anything:
        case datetime.datetime:
            return anything.isoformat()
        case models.Model:
            return str(anything.pk)
        case _:
            return str(anything)


def get_headers(sample=None, allowed_fields=allowed) -> abc.Iterable[str]:
    headers = [h for h in dir(sample) if allowed_fields(sample, h)]
    return headers


def fields(
    a: "bf_models.Asset", headers: abc.Iterable[str], formatter=formatter
) -> abc.Generator[typing.Any]:
    for h in headers:
        try:
            attr = getattr(a, h, None)
            yield formatter(attr)
        except exceptions.ObjectDoesNotExist:
            yield None


class Command(base.BaseCommand):
    """Django manage.py sub command dumps assets into a csv."""

    help = "Export assets as csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--filepath",
            type=str,
            required=False,
            help="The destination for the csv",
        )

    def handle(self, *_, **options) -> None:
        Asset = apps.get_model(app_label="blueflow", model_name="Asset")
        headers = get_headers(sample=Asset.objects.first())
        formatted_assets = []
        raw_assets = Asset.objects.all()
        for asset in raw_assets:
            a = list(fields(asset, headers))
            formatted_assets.append(a)

        file_path = options.get("filepath")
        if not file_path:
            file_path = DEFAULT_EXPORT
        with pathlib.Path(file_path).open(encoding="utf-8", mode="w") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(formatted_assets)
        count = Asset.objects.count()
        print(f"{count} assets written to {file_path}")  # noqa: T201
