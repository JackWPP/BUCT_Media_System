"""
SQLite → PostgreSQL data migration tool.

Reads all data from a SQLite .db file and imports it into a PostgreSQL database.
Handles type conversions (bool 0/1→true/false, JSON str→dict, datetime parsing)
and resets autoincrement sequences after import.

Usage:
    # Preview only
    python scripts/migrate_to_postgres.py \\
        --source visual_buct.db \\
        --target "postgresql://user:pass@host:5432/visual_buct" \\
        --dry-run

    # Full migration
    python scripts/migrate_to_postgres.py \\
        --source visual_buct.db \\
        --target "postgresql://user:pass@host:5432/visual_buct"

    # Truncate target tables first
    python scripts/migrate_to_postgres.py \\
        --source visual_buct.db \\
        --target "postgresql://user:pass@host:5432/visual_buct" \\
        --truncate
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

# Add project root to path so we can import models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ── Table definitions ──
# (table_name, columns, bool_columns, json_columns, pk_column for sequence reset)

TABLE_ORDER = [
    # ── base tables (no FK dependencies) ──
    {
        "name": "users",
        "bool_cols": ["is_active"],
        "json_cols": [],
        "autoincrement_pk": None,
    },
    {
        "name": "photos",
        "bool_cols": [],  # status/processing_status are text enums
        "json_cols": ["exif_data"],
        "autoincrement_pk": None,
    },
    {
        "name": "tags",
        "bool_cols": [],
        "json_cols": [],
        "autoincrement_pk": "id",
    },
    # ── taxonomy (FK: taxonomy_facets → taxonomy_nodes → taxonomy_aliases) ──
    {
        "name": "taxonomy_facets",
        "bool_cols": ["is_system", "is_active"],
        "json_cols": [],
        "autoincrement_pk": "id",
    },
    {
        "name": "taxonomy_nodes",
        "bool_cols": ["is_active"],
        "json_cols": [],
        "autoincrement_pk": "id",
    },
    {
        "name": "taxonomy_aliases",
        "bool_cols": [],
        "json_cols": [],
        "autoincrement_pk": "id",
    },
    # ── AI/task related ──
    {
        "name": "ai_analysis_tasks",
        "bool_cols": [],
        "json_cols": ["result_json"],
        "autoincrement_pk": None,
    },
    {
        "name": "ai_provider_configs",
        "bool_cols": ["enabled", "is_default"],
        "json_cols": ["extra_headers_json"],
        "autoincrement_pk": None,
    },
    {
        "name": "tasks",
        "bool_cols": [],
        "json_cols": [],
        "autoincrement_pk": None,
    },
    # ── system tables ──
    {
        "name": "system_configs",
        "bool_cols": [],
        "json_cols": [],
        "autoincrement_pk": None,
    },
    # ── join / association tables ──
    {
        "name": "photo_tags",
        "bool_cols": [],
        "json_cols": [],
        "autoincrement_pk": None,
    },
    {
        "name": "task_photos",
        "bool_cols": [],
        "json_cols": [],
        "autoincrement_pk": None,
    },
    {
        "name": "photo_classifications",
        "bool_cols": [],
        "json_cols": [],
        "autoincrement_pk": "id",
    },
    # ── features (FK to users + photos) ──
    {
        "name": "notifications",
        "bool_cols": ["is_read"],
        "json_cols": [],
        "autoincrement_pk": None,
    },
    {
        "name": "favorites",
        "bool_cols": [],
        "json_cols": [],
        "autoincrement_pk": None,
    },
    # ── permissions (FK to users) ──
    {
        "name": "resource_permissions",
        "bool_cols": [],
        "json_cols": [],
        "autoincrement_pk": None,
    },
    # ── audit (FK to users, nullable) ──
    {
        "name": "audit_logs",
        "bool_cols": [],
        "json_cols": [],
        "autoincrement_pk": None,
    },
]


def _convert_value(
    value: Any,
    col_name: str,
    bool_cols: list[str],
    json_cols: list[str],
) -> Any:
    """Convert SQLite-native value to PostgreSQL-compatible value."""
    if value is None:
        return None

    if col_name in bool_cols:
        if isinstance(value, bool):
            return value
        return bool(value)

    if col_name in json_cols:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    if isinstance(value, str):
        # Try ISO datetime parsing for timestamp columns
        if col_name.endswith("_at") and value:
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt
            except (ValueError, AttributeError):
                pass

    return value


def _row_to_dict(
    row: sqlite3.Row,
    bool_cols: list[str],
    json_cols: list[str],
) -> dict[str, Any]:
    """Convert a sqlite3.Row to a plain dict with type conversions applied."""
    result = {}
    for key in row.keys():
        result[key] = _convert_value(row[key], key, bool_cols, json_cols)
    return result


def _get_sqlite_conn(source_path: str) -> sqlite3.Connection:
    """Open and validate the SQLite source database."""
    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Source database not found: {path}")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _get_pg_engine(target_dsn: str) -> Engine:
    """Create and validate a PostgreSQL engine."""
    # Ensure we use a sync driver
    dsn = re.sub(r"^postgresql(\+[^:]+)?(?=://)", "postgresql+psycopg2", target_dsn)
    engine = create_engine(dsn)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return engine


def _count_rows(conn: sqlite3.Connection, table: str) -> int:
    cursor = conn.execute(f'SELECT COUNT(*) FROM "{table}"')
    return cursor.fetchone()[0]


def _get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cursor = conn.execute(f"PRAGMA table_info(\"{table}\")")
    return [row["name"] for row in cursor.fetchall()]


def migrate(
    source_path: str,
    target_dsn: str,
    *,
    dry_run: bool = False,
    truncate: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Run the full migration from SQLite to PostgreSQL.

    Returns a dict of {table_name: rows_migrated}.
    """
    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

    sqlite_conn = _get_sqlite_conn(source_path)

    if dry_run:
        log("=== DRY RUN — no data will be written ===")

    log(f"Source: {source_path}")
    log(f"Target: {target_dsn}")
    log(f"Tables to migrate: {len(TABLE_ORDER)}")

    pg_engine = None
    if not dry_run:
        pg_engine = _get_pg_engine(target_dsn)

    stats: dict[str, int] = {}

    for table_info in TABLE_ORDER:
        table_name = table_info["name"]
        bool_cols = table_info["bool_cols"]
        json_cols = table_info["json_cols"]
        autoincrement_pk = table_info["autoincrement_pk"]

        row_count = _count_rows(sqlite_conn, table_name)
        log(f"  {table_name}: {row_count} rows")

        if row_count == 0:
            stats[table_name] = 0
            continue

        if dry_run:
            stats[table_name] = row_count
            continue

        # Read all rows from SQLite
        columns = _get_columns(sqlite_conn, table_name)
        cursor = sqlite_conn.execute(f'SELECT * FROM "{table_name}"')
        rows = [_row_to_dict(r, bool_cols, json_cols) for r in cursor.fetchall()]

        if truncate:
            with pg_engine.begin() as conn:
                conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))

        # Write to PostgreSQL
        with pg_engine.begin() as conn:
            # Batch insert
            for row in rows:
                placeholders = ", ".join([f":{c}" for c in columns])
                col_names = ", ".join([f'"{c}"' for c in columns])
                sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
                # Handle ON CONFLICT for tables with PKs that might clash
                if table_name in ("photo_tags", "task_photos", "photo_classifications", "favorites"):
                    sql += " ON CONFLICT DO NOTHING"
                conn.execute(text(sql), row)

        # Reset autoincrement sequence
        if autoincrement_pk and rows:
            with pg_engine.begin() as conn:
                seq_name = f"{table_name}_{autoincrement_pk}_seq"
                conn.execute(
                    text(
                        f"SELECT setval('{seq_name}', "
                        f"COALESCE((SELECT MAX(\"{autoincrement_pk}\") FROM \"{table_name}\"), 1))"
                    )
                )

        stats[table_name] = len(rows)

    sqlite_conn.close()
    if pg_engine:
        pg_engine.dispose()

    log(f"\nDone. {sum(1 for v in stats.values() if v > 0)} tables, "
        f"{sum(stats.values())} total rows migrated.")

    return stats


# ── CLI entry point ──

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite to PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/migrate_to_postgres.py --source visual_buct.db --target "postgresql://postgres:pass@localhost:5432/visual_buct"
  python scripts/migrate_to_postgres.py --source visual_buct.db --target "postgresql://postgres:pass@localhost:5432/visual_buct" --dry-run
  python scripts/migrate_to_postgres.py --source visual_buct.db --target "postgresql://postgres:pass@localhost:5432/visual_buct" --truncate
        """,
    )
    parser.add_argument(
        "--source",
        default="visual_buct.db",
        help="Path to the SQLite .db file (default: visual_buct.db)",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="PostgreSQL DSN, e.g. postgresql://user:pass@host:5432/dbname",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate connections and count rows without writing",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate target tables before importing",
    )
    args = parser.parse_args()

    try:
        stats = migrate(
            source_path=args.source,
            target_dsn=args.target,
            dry_run=args.dry_run,
            truncate=args.truncate,
        )
        return 0
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
