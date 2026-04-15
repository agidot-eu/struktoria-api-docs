"""
db_importer.py — Import MSSQL database structure into a Struktoria RAG SQLite file.

For each database on the server the script extracts:
  - Tables     → markdown DDL (columns, PK, FK, indexes)
  - Views      → SQL definition
  - Stored procedures → SQL definition
  - Triggers   → SQL definition

Output path structure inside RAG:
  {database}/tables/{schema}.{table}
  {database}/views/{schema}.{view}
  {database}/procedures/{schema}.{procedure}
  {database}/triggers/{schema}.{trigger}

Usage:
  python db_importer.py \\
      --connection-string "DRIVER={ODBC Driver 18 for SQL Server};SERVER=myserver;UID=sa;PWD=secret" \\
      --output struktoria-db.sqlite \\
      [--databases db1,db2] \\
      [--no-procedures] \\
      [--no-triggers] \\
      [--no-views]

Requires:
  pip install pyodbc
  ODBC Driver 17 or 18 for SQL Server must be installed on the system.
"""

import argparse
import json
import re
import sys
from typing import Optional

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc is not installed. Run: pip install pyodbc", file=sys.stderr)
    sys.exit(1)

from schema import ImportDb


# ---------------------------------------------------------------------------
# SQL queries
# ---------------------------------------------------------------------------

SQL_LIST_DATABASES = """
SELECT name
FROM sys.databases
WHERE state_desc = 'ONLINE'
  AND name NOT IN ('master', 'tempdb', 'model', 'msdb')
ORDER BY name
"""

SQL_LIST_TABLES = """
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_SCHEMA, TABLE_NAME
"""

SQL_TABLE_COLUMNS = """
SELECT
    c.COLUMN_NAME,
    c.DATA_TYPE,
    c.CHARACTER_MAXIMUM_LENGTH,
    c.NUMERIC_PRECISION,
    c.NUMERIC_SCALE,
    c.IS_NULLABLE,
    c.COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS c
WHERE c.TABLE_SCHEMA = ? AND c.TABLE_NAME = ?
ORDER BY c.ORDINAL_POSITION
"""

SQL_PRIMARY_KEY = """
SELECT kcu.COLUMN_NAME
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
    ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
    AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
  AND tc.TABLE_SCHEMA = ?
  AND tc.TABLE_NAME = ?
ORDER BY kcu.ORDINAL_POSITION
"""

SQL_FOREIGN_KEYS = """
SELECT
    fk.name AS fk_name,
    OBJECT_SCHEMA_NAME(fkc.parent_object_id) AS parent_schema,
    OBJECT_NAME(fkc.parent_object_id)        AS parent_table,
    COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS parent_col,
    OBJECT_SCHEMA_NAME(fkc.referenced_object_id) AS ref_schema,
    OBJECT_NAME(fkc.referenced_object_id)        AS ref_table,
    COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS ref_col
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
WHERE OBJECT_SCHEMA_NAME(fkc.parent_object_id) = ?
  AND OBJECT_NAME(fkc.parent_object_id) = ?
ORDER BY fk.name
"""

SQL_INDEXES = """
SELECT
    i.name AS index_name,
    i.is_unique,
    i.is_primary_key,
    STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
FROM sys.indexes i
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE i.object_id = OBJECT_ID(? + '.' + ?)
  AND i.is_primary_key = 0
  AND i.type > 0
GROUP BY i.name, i.is_unique, i.is_primary_key
ORDER BY i.name
"""

SQL_LIST_VIEWS = """
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.VIEWS
ORDER BY TABLE_SCHEMA, TABLE_NAME
"""

SQL_MODULE_DEFINITION = """
SELECT sm.definition
FROM sys.objects o
JOIN sys.sql_modules sm ON o.object_id = sm.object_id
WHERE o.schema_id = SCHEMA_ID(?) AND o.name = ?
"""

SQL_LIST_PROCEDURES = """
SELECT ROUTINE_SCHEMA, ROUTINE_NAME
FROM INFORMATION_SCHEMA.ROUTINES
WHERE ROUTINE_TYPE = 'PROCEDURE'
ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME
"""

SQL_LIST_TRIGGERS = """
SELECT
    OBJECT_SCHEMA_NAME(t.object_id) AS trigger_schema,
    t.name AS trigger_name,
    OBJECT_NAME(t.parent_id) AS parent_table
FROM sys.triggers t
WHERE t.is_ms_shipped = 0
  AND t.parent_class = 1  -- table triggers only
ORDER BY trigger_schema, trigger_name
"""

SQL_TRIGGER_DEFINITION = """
SELECT sm.definition
FROM sys.triggers t
JOIN sys.sql_modules sm ON t.object_id = sm.object_id
WHERE t.name = ? AND OBJECT_SCHEMA_NAME(t.object_id) = ?
"""


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------

def _col_type(row) -> str:
    dt = row.DATA_TYPE
    if row.CHARACTER_MAXIMUM_LENGTH:
        length = "MAX" if row.CHARACTER_MAXIMUM_LENGTH == -1 else str(row.CHARACTER_MAXIMUM_LENGTH)
        return f"{dt}({length})"
    if row.NUMERIC_PRECISION and dt in ("decimal", "numeric"):
        return f"{dt}({row.NUMERIC_PRECISION},{row.NUMERIC_SCALE or 0})"
    return dt


def build_table_markdown(cur, db: str, schema: str, table: str) -> str:
    lines = [f"# Table: {schema}.{table} [{db}]\n"]

    # Columns
    cur.execute(SQL_TABLE_COLUMNS, (schema, table))
    cols = cur.fetchall()
    if cols:
        lines.append("## Columns\n")
        lines.append("| Column | Type | Nullable | Default |")
        lines.append("|--------|------|----------|---------|")
        for c in cols:
            default = c.COLUMN_DEFAULT or ""
            nullable = c.IS_NULLABLE
            lines.append(f"| {c.COLUMN_NAME} | {_col_type(c)} | {nullable} | {default} |")
        lines.append("")

    # Primary key
    cur.execute(SQL_PRIMARY_KEY, (schema, table))
    pk_cols = [r[0] for r in cur.fetchall()]
    if pk_cols:
        lines.append(f"## Primary Key: ({', '.join(pk_cols)})\n")

    # Foreign keys
    cur.execute(SQL_FOREIGN_KEYS, (schema, table))
    fks = cur.fetchall()
    if fks:
        lines.append("## Foreign Keys\n")
        for fk in fks:
            lines.append(
                f"- {fk.fk_name}: {fk.parent_col} → {fk.ref_schema}.{fk.ref_table}.{fk.ref_col}"
            )
        lines.append("")

    # Indexes
    try:
        cur.execute(SQL_INDEXES, (schema, table))
        idxs = cur.fetchall()
        if idxs:
            lines.append("## Indexes\n")
            for idx in idxs:
                unique = " UNIQUE" if idx.is_unique else ""
                lines.append(f"- {idx.index_name}{unique}: ({idx.columns})")
            lines.append("")
    except pyodbc.Error:
        pass  # STRING_AGG requires SQL Server 2017+; skip gracefully

    return "\n".join(lines)


def build_object_markdown(title: str, definition: Optional[str]) -> str:
    if not definition:
        return f"# {title}\n\n*(definition not available)*\n"
    return f"# {title}\n\n```sql\n{definition.strip()}\n```\n"


# ---------------------------------------------------------------------------
# Sanitize connection string for storage (remove password)
# ---------------------------------------------------------------------------

def sanitize_cs(cs: str) -> str:
    return re.sub(r"(?i)(PWD|PASSWORD)\s*=\s*[^;]+", r"\1=***", cs)


# ---------------------------------------------------------------------------
# Main import logic
# ---------------------------------------------------------------------------

def import_database(
    connection_string: str,
    output_path: str,
    databases_filter: Optional[list[str]],
    include_procedures: bool,
    include_triggers: bool,
    include_views: bool,
):
    print(f"Connecting to SQL Server...")
    conn = pyodbc.connect(connection_string, timeout=30)
    conn.autocommit = True  # required for USE statements
    cur = conn.cursor()

    cur.execute(SQL_LIST_DATABASES)
    all_dbs = [row[0] for row in cur.fetchall()]

    if databases_filter:
        dbs = [d for d in all_dbs if d in databases_filter]
        missing = set(databases_filter) - set(all_dbs)
        if missing:
            print(f"WARNING: databases not found on server: {', '.join(sorted(missing))}", file=sys.stderr)
    else:
        dbs = all_dbs

    print(f"Databases to import: {', '.join(dbs)}")

    with ImportDb(output_path) as db:
        session_id = db.create_session(
            source_type="mssql",
            source_name=sanitize_cs(connection_string),
        )
        total = 0

        for database in dbs:
            print(f"\n[{database}] Importing...")
            cur.execute(f"USE [{database}]")

            # --- Tables ---
            cur.execute(SQL_LIST_TABLES)
            tables = cur.fetchall()
            print(f"  Tables:     {len(tables)}")
            for schema, table in tables:
                content = build_table_markdown(cur, database, schema, table)
                db.upsert_node(
                    session_id=session_id,
                    relative_path=f"{database}/tables/{schema}.{table}",
                    content=content,
                    node_type="document",
                    source_type="mssql",
                    source_path=f"{database}.{schema}.{table}",
                    meta_json=json.dumps({
                        "type": "table",
                        "db": database,
                        "schema": schema,
                        "object": table,
                        "source": "mssql",
                    }),
                )
                total += 1
            db.flush()

            # --- Views ---
            if include_views:
                cur.execute(SQL_LIST_VIEWS)
                views = cur.fetchall()
                print(f"  Views:      {len(views)}")
                for schema, view in views:
                    cur2 = conn.cursor()
                    cur2.execute(f"USE [{database}]")
                    cur2.execute(SQL_MODULE_DEFINITION, (schema, view))
                    row = cur2.fetchone()
                    definition = row[0] if row else None
                    content = build_object_markdown(f"View: {schema}.{view} [{database}]", definition)
                    db.upsert_node(
                        session_id=session_id,
                        relative_path=f"{database}/views/{schema}.{view}",
                        content=content,
                        node_type="document",
                        source_type="mssql",
                        source_path=f"{database}.{schema}.{view}",
                        meta_json=json.dumps({
                            "type": "view",
                            "db": database,
                            "schema": schema,
                            "object": view,
                            "source": "mssql",
                        }),
                    )
                    total += 1
                db.flush()

            # --- Stored Procedures ---
            if include_procedures:
                cur.execute(SQL_LIST_PROCEDURES)
                procs = cur.fetchall()
                print(f"  Procedures: {len(procs)}")
                for schema, proc in procs:
                    cur2 = conn.cursor()
                    cur2.execute(f"USE [{database}]")
                    cur2.execute(SQL_MODULE_DEFINITION, (schema, proc))
                    row = cur2.fetchone()
                    definition = row[0] if row else None
                    content = build_object_markdown(f"Procedure: {schema}.{proc} [{database}]", definition)
                    db.upsert_node(
                        session_id=session_id,
                        relative_path=f"{database}/procedures/{schema}.{proc}",
                        content=content,
                        node_type="document",
                        source_type="mssql",
                        source_path=f"{database}.{schema}.{proc}",
                        meta_json=json.dumps({
                            "type": "procedure",
                            "db": database,
                            "schema": schema,
                            "object": proc,
                            "source": "mssql",
                        }),
                    )
                    total += 1
                db.flush()

            # --- Triggers ---
            if include_triggers:
                cur.execute(SQL_LIST_TRIGGERS)
                triggers = cur.fetchall()
                print(f"  Triggers:   {len(triggers)}")
                for trig_schema, trig_name, parent_table in triggers:
                    cur2 = conn.cursor()
                    cur2.execute(f"USE [{database}]")
                    cur2.execute(SQL_TRIGGER_DEFINITION, (trig_name, trig_schema))
                    row = cur2.fetchone()
                    definition = row[0] if row else None
                    title = f"Trigger: {trig_schema}.{trig_name} on {parent_table} [{database}]"
                    content = build_object_markdown(title, definition)
                    db.upsert_node(
                        session_id=session_id,
                        relative_path=f"{database}/triggers/{trig_schema}.{trig_name}",
                        content=content,
                        node_type="document",
                        source_type="mssql",
                        source_path=f"{database}.{trig_schema}.{trig_name}",
                        meta_json=json.dumps({
                            "type": "trigger",
                            "db": database,
                            "schema": trig_schema,
                            "object": trig_name,
                            "parent_table": parent_table,
                            "source": "mssql",
                        }),
                    )
                    total += 1
                db.flush()

        print(f"\nDone. Total nodes written: {total}")
        print(f"Output: {output_path}  (session: {session_id})")

    conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Import MSSQL database structure into a Struktoria RAG SQLite file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--connection-string", "-c",
        required=True,
        help='ODBC connection string, e.g. "DRIVER={ODBC Driver 18 for SQL Server};SERVER=myhost;UID=sa;PWD=secret"',
    )
    parser.add_argument(
        "--output", "-o",
        default="struktoria-db.sqlite",
        help="Output SQLite file path (default: struktoria-db.sqlite)",
    )
    parser.add_argument(
        "--databases", "-d",
        help="Comma-separated list of databases to import (default: all user databases)",
    )
    parser.add_argument(
        "--no-procedures",
        action="store_true",
        help="Skip stored procedures",
    )
    parser.add_argument(
        "--no-triggers",
        action="store_true",
        help="Skip triggers",
    )
    parser.add_argument(
        "--no-views",
        action="store_true",
        help="Skip views",
    )

    args = parser.parse_args()

    databases_filter = None
    if args.databases:
        databases_filter = [d.strip() for d in args.databases.split(",") if d.strip()]

    import_database(
        connection_string=args.connection_string,
        output_path=args.output,
        databases_filter=databases_filter,
        include_procedures=not args.no_procedures,
        include_triggers=not args.no_triggers,
        include_views=not args.no_views,
    )


if __name__ == "__main__":
    main()
