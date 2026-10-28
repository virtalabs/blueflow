"""Tests for the export_assets management command."""

import csv
import datetime

from django.core import management
from model_bakery import baker

from blueflow import models
from blueflow.management.commands import export_assets


def export(tmp_path) -> list[list[str]]:
    path = tmp_path / "out.csv"
    management.call_command("export_assets", filepath=str(path))
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.reader(f, strict=True))


def export_dicts(tmp_path) -> list[dict[str, str]]:
    header, *rows = export(tmp_path)
    return [dict(zip(header, row, strict=True)) for row in rows]


def test_export_data_correct(db, tmp_path):
    assets = [
        baker.make("Asset", name="alpha", hostname="alpha.local", os="Linux"),
        baker.make("Asset", name="beta", hostname="beta.local", os="Windows"),
    ]
    rows = {row["id"]: row for row in export_dicts(tmp_path)}
    for asset in assets:
        row = rows[str(asset.pk)]
        assert row["name"] == asset.name
        assert row["hostname"] == asset.hostname
        assert row["os"] == asset.os


def test_export_headers(db, tmp_path):
    baker.make("Asset")
    header = export(tmp_path)[0]
    expected = export_assets.get_headers(sample=models.Asset.objects.first())
    assert header == list(expected)
    assert {"id", "name", "hostname", "last_scanned", "created"} <= set(header)
    assert not {"objects", "_meta", "_state"} & set(header)
    assert not [h for h in header if "__" in h]


def test_export_none_is_empty_string(db, tmp_path):
    baker.make("Asset", hostname=None, external_keys=None)
    (row,) = export_dicts(tmp_path)
    assert row["hostname"] == ""
    assert row["external_keys"] == ""


def test_export_datetimes_iso(db, tmp_path):
    stamp = datetime.datetime(2026, 1, 2, 3, 4, 5, 678000, tzinfo=datetime.UTC)
    asset = baker.make("Asset", last_scanned=stamp, last_pinged=stamp)
    asset.refresh_from_db()
    (row,) = export_dicts(tmp_path)
    for field in ("last_scanned", "last_pinged"):
        assert row[field] == stamp.isoformat()
        assert datetime.datetime.fromisoformat(row[field]) == stamp
    for field in ("created", "modified"):
        value = getattr(asset, field)
        assert datetime.datetime.fromisoformat(row[field]) == value


def test_export_row_count(db, tmp_path):
    baker.make("Asset", _quantity=5)
    assert len(export(tmp_path)) == models.Asset.objects.count() + 1


def test_export_is_valid_csv(db, tmp_path):
    tricky = 'a, "b"\nc'
    baker.make("Asset", name=tricky)
    header, *rows = export(tmp_path)
    assert all(len(row) == len(header) for row in rows)
    (row,) = rows
    assert row[header.index("name")] == tricky
