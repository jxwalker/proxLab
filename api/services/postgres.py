"""
Postgres provisioning service.
Connects to the shared Postgres LXC as superuser via POSTGRES_DSN.
Creates per-service databases with dedicated users and random passwords.
"""
from __future__ import annotations

import secrets
import string
from typing import Optional

import asyncpg

from api.config import settings

# System databases to exclude from list output
_SYSTEM_DBS = {"postgres", "template0", "template1"}


def _random_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(settings.postgres_dsn)


# ---------------------------------------------------------------------------
# Database management
# ---------------------------------------------------------------------------

async def list_databases() -> list[dict]:
    """List all non-system databases with size and owner."""
    conn = await _connect()
    try:
        rows = await conn.fetch("""
            SELECT
                d.datname AS name,
                r.rolname AS owner,
                pg_database_size(d.datname) AS size_bytes
            FROM pg_database d
            JOIN pg_roles r ON r.oid = d.datdba
            WHERE d.datistemplate = false
              AND d.datname NOT IN ('postgres')
            ORDER BY d.datname
        """)
        return [
            {
                "name": row["name"],
                "owner": row["owner"],
                "size_mb": round(row["size_bytes"] / 1024**2, 2),
            }
            for row in rows
            if row["name"] not in _SYSTEM_DBS
        ]
    finally:
        await conn.close()


async def create_database(name: str, owner: Optional[str] = None) -> dict:
    """
    Create a database, a matching user, and grant all privileges.
    Returns a dict including the connection string.
    """
    username = owner or name
    password = _random_password()

    conn = await _connect()
    try:
        # Create user (role) if it doesn't exist
        existing = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = $1", username
        )
        if not existing:
            # asyncpg doesn't support parameterised DDL identifiers
            await conn.execute(
                f'CREATE USER "{username}" WITH PASSWORD \'{password}\''
            )
        else:
            # Reset password on re-creation
            await conn.execute(
                f"ALTER USER \"{username}\" WITH PASSWORD '{password}'"
            )

        # Create the database owned by the user
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", name
        )
        if not db_exists:
            await conn.execute(
                f'CREATE DATABASE "{name}" OWNER "{username}"'
            )
        else:
            await conn.execute(
                f'ALTER DATABASE "{name}" OWNER TO "{username}"'
            )

        # Grant all privileges
        await conn.execute(
            f'GRANT ALL PRIVILEGES ON DATABASE "{name}" TO "{username}"'
        )
    finally:
        await conn.close()

    # Build connection string using the host from settings DSN
    import urllib.parse
    parsed = urllib.parse.urlparse(settings.postgres_dsn)
    host = parsed.hostname
    port = parsed.port or 5432
    connection_string = f"postgresql://{username}:{password}@{host}:{port}/{name}"

    return {
        "name": name,
        "owner": username,
        "size_mb": 0.0,
        "connection_string": connection_string,
    }


async def drop_database(name: str) -> None:
    """Drop a database and its owner role."""
    conn = await _connect()
    try:
        # Terminate existing connections — use $1 to avoid SQL injection
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            name,
        )
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", name
        )
        if db_exists:
            await conn.execute(f'DROP DATABASE "{name}"')

        # Drop the owner role if it matches the DB name and has no other DBs
        role_exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = $1", name
        )
        if role_exists:
            other_dbs = await conn.fetchval(
                "SELECT count(*) FROM pg_database WHERE datdba = "
                "(SELECT oid FROM pg_roles WHERE rolname = $1)",
                name,
            )
            if other_dbs == 0:
                await conn.execute(f'DROP ROLE "{name}"')
    finally:
        await conn.close()


async def get_database(name: str) -> Optional[dict]:
    """Get database info including size."""
    conn = await _connect()
    try:
        row = await conn.fetchrow("""
            SELECT d.datname, r.rolname AS owner, pg_database_size(d.datname) AS size_bytes
            FROM pg_database d
            JOIN pg_roles r ON r.oid = d.datdba
            WHERE d.datname = $1
        """, name)
        if not row:
            return None
        import urllib.parse
        parsed = urllib.parse.urlparse(settings.postgres_dsn)
        host = parsed.hostname
        port = parsed.port or 5432
        # Note: password is not stored — user must have created it via create_database
        connection_string = f"postgresql://{row['owner']}:***@{host}:{port}/{name}"
        return {
            "name": row["datname"],
            "owner": row["owner"],
            "size_mb": round(row["size_bytes"] / 1024**2, 2),
            "connection_string": connection_string,
        }
    finally:
        await conn.close()
