#!/usr/bin/env python
"""
Migration: add 'updated_rows' JSON column to workspace_cast_rows,
workspace_corent_rows, and workspace_biz_rows tables.

Safe to run multiple times — silently skips columns that already exist.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

TABLES = [
    "workspace_cast_rows",
    "workspace_corent_rows",
    "workspace_biz_rows",
]


def column_exists(connection, table: str, column: str) -> bool:
    result = connection.execute(db.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result.fetchall())


def run_migration():
    app = create_app('development')
    with app.app_context():
        conn = db.engine.connect()
        for table in TABLES:
            if not column_exists(conn, table, "updated_rows"):
                conn.execute(db.text(
                    f"ALTER TABLE {table} ADD COLUMN updated_rows TEXT"
                ))
                conn.commit()
                print(f"[OK] Added 'updated_rows' to {table}")
            else:
                print(f"[SKIP] '{table}.updated_rows' already exists")
        conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    run_migration()
