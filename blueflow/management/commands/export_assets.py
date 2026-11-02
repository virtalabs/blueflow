import csv
import pathlib

from django.apps import apps
from django.core.management import base

DEFAULT_EXPORT = "/tmp/assets.csv"  # noqa: S108 # nosec


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
        headers = Asset.export_headers()

        file_path = options.get("filepath")
        if not file_path:
            file_path = DEFAULT_EXPORT
        formatted_assets = Asset.export()
        with pathlib.Path(file_path).open(encoding="utf-8", mode="w") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(formatted_assets)
        count = Asset.objects.count()
        self.stdout.write(f"{count} assets written to {file_path}")
