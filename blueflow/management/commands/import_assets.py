import csv
import pathlib

from django.apps import apps
from django.core.management import base


class Command(base.BaseCommand):
    """Django manage.py sub command loads assets from a csv."""

    help = "Import assets from csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--filepath",
            type=str,
            required=True,
            help="The source csv",
        )

    def handle(self, *_, **options) -> None:
        Asset = apps.get_model(app_label="blueflow", model_name="Asset")
        file_path = options["filepath"]
        with pathlib.Path(file_path).open(encoding="utf-8", newline="") as file:
            created, updated = Asset.import_rows(csv.DictReader(file))
        self.stdout.write(f"{created} created, {updated} updated from {file_path}")
