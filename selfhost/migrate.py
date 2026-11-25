#!/usr/bin/env python3
"""Apply MacroDB migrations with psql.

SQLx's table is filled so a later `sqlx migrate` sees the same versions.
Checksums are SHA-384 of the file bytes, which is what SQLx records.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "crates" / "macro_db_client" / "migrations"


def load_env() -> None:
    path = Path(__file__).resolve().parent / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def psql(sql: str, database: str = "macrodb") -> None:
    env = os.environ.copy()
    command = [
        *os.environ.get("SELFHOST_DOCKER", "docker").split(),
        "compose",
        "--project-directory",
        str(ROOT / "selfhost"),
        "exec",
        "-T",
        "postgres",
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        env.get("POSTGRES_USER", "macro"),
        "-d",
        database,
    ]
    result = subprocess.run(command, input=sql.encode(), check=False)
    if result.returncode != 0:
        raise SystemExit(f"psql failed ({result.returncode})")


def psql_file(path: Path) -> None:
    env = os.environ.copy()
    command = [
        *os.environ.get("SELFHOST_DOCKER", "docker").split(),
        "compose",
        "--project-directory",
        str(ROOT / "selfhost"),
        "exec",
        "-T",
        "postgres",
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        env.get("POSTGRES_USER", "macro"),
        "-d",
        "macrodb",
    ]
    result = subprocess.run(command, input=path.read_bytes(), check=False)
    if result.returncode != 0:
        raise SystemExit(f"migration failed: {path.name}")


def applied() -> set[int]:
    command = [
        *os.environ.get("SELFHOST_DOCKER", "docker").split(),
        "compose",
        "--project-directory",
        str(ROOT / "selfhost"),
        "exec",
        "-T",
        "postgres",
        "psql",
        "-q",
        "-tA",
        "-U",
        os.environ.get("POSTGRES_USER", "macro"),
        "-d",
        "macrodb",
        "-c",
        "SELECT version FROM _sqlx_migrations WHERE success",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        return set()
    versions: set[int] = set()
    for line in result.stdout.decode().splitlines():
        line = line.strip()
        if line.isdigit():
            versions.add(int(line))
    return versions


def main() -> None:
    load_env()
    psql(
        """
        CREATE TABLE IF NOT EXISTS _sqlx_migrations (
            version BIGINT PRIMARY KEY,
            description TEXT NOT NULL,
            installed_on TIMESTAMPTZ NOT NULL DEFAULT now(),
            success BOOLEAN NOT NULL,
            checksum BYTEA NOT NULL,
            execution_time BIGINT NOT NULL
        );
        """,
        database=os.environ.get("POSTGRES_DB", "macrodb"),
    )
    done = applied()
    files = sorted(MIGRATIONS.glob("*.sql"))
    for path in files:
        version_text, _, description = path.name.partition("_")
        if not version_text.isdigit():
            continue
        version = int(version_text)
        if version in done:
            continue
        print(f"migrate {path.name}", flush=True)
        psql_file(path)
        checksum = hashlib.sha384(path.read_bytes()).hexdigest()
        description_sql = description.removesuffix(".sql").replace("'", "''")
        psql(
            f"""
            INSERT INTO _sqlx_migrations
                (version, description, success, checksum, execution_time)
            VALUES
                ({version}, '{description_sql}', true, decode('{checksum}', 'hex'), 0);
            """
        )
    print(f"migrations applied ({len(files)} files)", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
