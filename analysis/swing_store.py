#!/usr/bin/env python3
"""Merge swing exports into the Mac swing database (data/raw/swings.json)."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from analysis.analyze_swings import load_records
except ImportError:
    from analyze_swings import load_records

DEFAULT_DATABASE = Path("data/raw/swings.json")
DEFAULT_ARCHIVE_DIR = Path("data/exports")
DEFAULT_OUTPUT_DIR = Path("analysis/output")


@dataclass(frozen=True)
class MergeResult:
    added: int
    updated: int
    unchanged: int
    total: int
    archived_path: Path | None


def _record_id(record: dict[str, Any]) -> str:
    swing_id = record.get("id")
    if not swing_id:
        raise ValueError("Swing record is missing required field 'id'.")
    return str(swing_id)


def _index_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        indexed[_record_id(record)] = record
    return indexed


def merge_records(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], MergeResult]:
    """Merge incoming swings into existing by id. Mac-only swings are kept."""
    existing_by_id = _index_records(existing)
    incoming_by_id = _index_records(incoming)

    added = 0
    updated = 0
    unchanged = 0

    for swing_id, record in incoming_by_id.items():
        if swing_id not in existing_by_id:
            existing_by_id[swing_id] = record
            added += 1
            continue

        if existing_by_id[swing_id] != record:
            existing_by_id[swing_id] = record
            updated += 1
        else:
            unchanged += 1

    merged = sorted(
        existing_by_id.values(),
        key=lambda item: str(item.get("date") or ""),
    )
    result = MergeResult(
        added=added,
        updated=updated,
        unchanged=unchanged,
        total=len(merged),
        archived_path=None,
    )
    return merged, result


def save_records(database_path: Path, records: list[dict[str, Any]]) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_database(database_path: Path) -> list[dict[str, Any]]:
    if not database_path.exists():
        return []
    return load_records(database_path)


def archive_export(
    source_path: Path,
    archive_dir: Path,
    *,
    timestamp: datetime | None = None,
) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = (timestamp or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    destination = archive_dir / f"{stamp}_{source_path.name}"
    shutil.copy2(source_path, destination)
    return destination


def merge_import_file(
    input_path: Path,
    *,
    database_path: Path = DEFAULT_DATABASE,
    archive_dir: Path = DEFAULT_ARCHIVE_DIR,
    archive: bool = True,
) -> MergeResult:
    incoming = load_records(input_path)
    existing = load_database(database_path)
    merged, result = merge_records(existing, incoming)

    archived_path = archive_export(input_path, archive_dir) if archive else None
    save_records(database_path, merged)
    return MergeResult(
        added=result.added,
        updated=result.updated,
        unchanged=result.unchanged,
        total=result.total,
        archived_path=archived_path,
    )


def delete_records(
    database_path: Path,
    swing_ids: set[str],
) -> tuple[list[dict[str, Any]], int]:
    existing = load_database(database_path)
    kept = [record for record in existing if _record_id(record) not in swing_ids]
    removed = len(existing) - len(kept)
    save_records(database_path, kept)
    return kept, removed


def rebuild_features(
    database_path: Path = DEFAULT_DATABASE,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> int:
    try:
        from analysis.analyze_swings import extract_features
        from analysis.swing_trim import trim_json_file
    except ImportError:
        from analyze_swings import extract_features
        from swing_trim import trim_json_file

    import pandas as pd

    trim_json_file(database_path)
    records = load_records(database_path)
    features = [extract_features(record) for record in records]

    output_dir.mkdir(parents=True, exist_ok=True)
    features_df = pd.DataFrame(features)
    csv_path = output_dir / "swing_features.csv"
    parquet_path = output_dir / "swing_features.parquet"
    features_df.to_csv(csv_path, index=False)
    features_df.to_parquet(parquet_path, index=False)
    return len(records)


def _parse_ids(raw_ids: list[str]) -> set[str]:
    return {item.strip() for item in raw_ids if item.strip()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage the Mac swing database (merge imports, list, delete)."
    )
    parser.add_argument(
        "--database",
        default=str(DEFAULT_DATABASE),
        help="Path to accumulated swings JSON (default: data/raw/swings.json)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Feature output directory for rebuild (default: analysis/output)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    merge_parser = subparsers.add_parser("merge", help="Merge an export into the database")
    merge_parser.add_argument("--input", required=True, help="Path to golf_swings_export.json")
    merge_parser.add_argument(
        "--archive-dir",
        default=str(DEFAULT_ARCHIVE_DIR),
        help="Folder for dated export copies (default: data/exports)",
    )
    merge_parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Skip copying the incoming export to data/exports/",
    )
    merge_parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild feature tables after merge",
    )

    delete_parser = subparsers.add_parser("delete", help="Remove swings by id from the database")
    delete_parser.add_argument("--id", action="append", default=[], dest="ids")
    delete_parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild feature tables after delete",
    )

    subparsers.add_parser("list", help="List swing ids in the database")
    subparsers.add_parser("stats", help="Show database counts")

    subparsers.add_parser("rebuild", help="Rebuild feature tables from database")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_path = Path(args.database).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if args.command == "merge":
        result = merge_import_file(
            Path(args.input).expanduser().resolve(),
            database_path=database_path,
            archive_dir=Path(args.archive_dir).expanduser().resolve(),
            archive=not args.no_archive,
        )
        print(
            f"Merged import: +{result.added} new, {result.updated} updated, "
            f"{result.unchanged} unchanged → {result.total} total in {database_path}"
        )
        if result.archived_path:
            print(f"Archived export: {result.archived_path}")
        if args.rebuild:
            count = rebuild_features(database_path, output_dir)
            print(f"Rebuilt {count} swing(s) in {output_dir}")
        return

    if args.command == "delete":
        swing_ids = _parse_ids(args.ids)
        if not swing_ids:
            raise SystemExit("Provide at least one --id to delete.")
        _, removed = delete_records(database_path, swing_ids)
        remaining = len(load_database(database_path))
        print(f"Removed {removed} swing(s). {remaining} remain in {database_path}.")
        if args.rebuild:
            count = rebuild_features(database_path, output_dir)
            print(f"Rebuilt {count} swing(s) in {output_dir}")
        return

    if args.command == "list":
        records = load_database(database_path)
        if not records:
            print(f"No swings in {database_path}")
            return
        for record in records:
            swing_id = _record_id(record)
            date = record.get("date", "?")
            club = record.get("club", "?")
            rating = record.get("rating", "?")
            print(f"{swing_id}  {date}  {club}  rating={rating}")
        return

    if args.command == "stats":
        records = load_database(database_path)
        print(f"database: {database_path}")
        print(f"swings:   {len(records)}")
        archive_dir = DEFAULT_ARCHIVE_DIR
        if archive_dir.exists():
            archives = sorted(archive_dir.glob("*.json"))
            print(f"archives: {len(archives)} in {archive_dir}")
        return

    if args.command == "rebuild":
        count = rebuild_features(database_path, output_dir)
        print(f"Rebuilt {count} swing(s) in {output_dir}")


if __name__ == "__main__":
    main()
