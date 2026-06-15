from __future__ import annotations

from pathlib import Path

from analysis.swing_store import (
    delete_records,
    load_database,
    merge_import_file,
    merge_records,
    save_records,
)


def _record(swing_id: str, rating: int = 3, club: str = "7I") -> dict:
    return {
        "id": swing_id,
        "date": "2026-06-15T10:00:00Z",
        "rating": rating,
        "club": club,
        "samples": [{"timestamp": 0.0, "accelX": 0.0, "accelY": 0.0, "accelZ": 1.0}],
    }


def test_merge_records_adds_new_swings() -> None:
    existing = [_record("a")]
    incoming = [_record("b")]
    merged, result = merge_records(existing, incoming)
    assert result.added == 1
    assert result.total == 2
    assert {item["id"] for item in merged} == {"a", "b"}


def test_merge_records_keeps_mac_only_swings() -> None:
    existing = [_record("a"), _record("b")]
    incoming = [_record("c")]
    merged, result = merge_records(existing, incoming)
    assert result.added == 1
    assert result.total == 3
    assert {item["id"] for item in merged} == {"a", "b", "c"}


def test_merge_records_updates_existing_id() -> None:
    existing = [_record("a", rating=3)]
    incoming = [_record("a", rating=5)]
    merged, result = merge_records(existing, incoming)
    assert result.updated == 1
    assert merged[0]["rating"] == 5


def test_merge_import_file_archives_and_persists(tmp_path: Path) -> None:
    database = tmp_path / "swings.json"
    archive_dir = tmp_path / "exports"
    incoming_path = tmp_path / "incoming.json"

    save_records(database, [_record("a")])
    save_records(incoming_path, [_record("b")])

    result = merge_import_file(
        incoming_path,
        database_path=database,
        archive_dir=archive_dir,
    )

    assert result.added == 1
    assert result.total == 2
    assert result.archived_path is not None
    assert result.archived_path.exists()
    assert len(list(archive_dir.glob("*.json"))) == 1


def test_delete_records_removes_by_id(tmp_path: Path) -> None:
    database = tmp_path / "swings.json"
    save_records(database, [_record("a"), _record("b")])

    _, removed = delete_records(database, {"a"})
    assert removed == 1

    remaining = load_database(database)
    assert len(remaining) == 1
    assert remaining[0]["id"] == "b"
