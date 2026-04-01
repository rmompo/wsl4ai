"""Resolve ``wsls``, ``registries``, and ``uses`` for ``use`` / ``wsl`` commands."""

import re
import sqlite3
import uuid

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_uuid(value: str) -> bool:
    return bool(_UUID_RE.match((value or "").strip()))


def new_uuid() -> str:
    return str(uuid.uuid4())


def ensure_wsls_row(con: sqlite3.Connection, name: str, user: str) -> str:
    """Insert ``wsls`` row with ``cli_command NULL`` if missing; return ``uuid``."""
    name = (name or "").strip()
    user = (user or "").strip()
    row = con.execute(
        "SELECT uuid FROM wsls WHERE LOWER(name) = LOWER(?) AND user = ?",
        (name, user),
    ).fetchone()
    if row:
        return row[0]
    uid = new_uuid()
    con.execute(
        "INSERT INTO wsls (uuid, name, user, cli_command) VALUES (?, ?, ?, NULL)",
        (uid, name, user),
    )
    return uid


def resolve_wsl_uuid(
    con: sqlite3.Connection,
    *,
    wsl_uuid: str,
    wsl_name: str,
    runtime_user: str,
    runtime_wsl_name: str,
    create_if_missing: bool,
    msg_prefix: str = "use",
) -> tuple[str | None, str | None]:
    """Return ``(wsl_uuid, None)`` or ``(None, error_message)``."""
    wu = (wsl_uuid or "").strip()
    wn = (wsl_name or "").strip()
    p = msg_prefix
    if wu:
        if not is_uuid(wu):
            return None, f"{p}: invalid --wsl-uuid"
        row = con.execute("SELECT uuid FROM wsls WHERE uuid = ?", (wu,)).fetchone()
        if not row:
            return None, f"{p}: wsl not found (--wsl-uuid)"
        return row[0], None
    if wn:
        row = con.execute(
            "SELECT uuid FROM wsls WHERE LOWER(name) = LOWER(?) AND user = ?",
            (wn, runtime_user),
        ).fetchone()
        if row:
            return row[0], None
        if create_if_missing:
            return ensure_wsls_row(con, wn, runtime_user), None
        return None, f"{p}: wsl not found (--wsl-name); run use add first or check name/user"
    row = con.execute(
        "SELECT uuid FROM wsls WHERE LOWER(name) = LOWER(?) AND user = ?",
        (runtime_wsl_name, runtime_user),
    ).fetchone()
    if row:
        return row[0], None
    if create_if_missing:
        return ensure_wsls_row(con, runtime_wsl_name, runtime_user), None
    return None, f"{p}: wsl not found (runtime identity); run use add first"


def resolve_registry_target(
    con: sqlite3.Connection,
    *,
    registry_uuid: str,
    registry_name: str,
    prefix: str = "use",
) -> tuple[str | None, str | None]:
    """Resolve ``registries.uuid`` from uuid or name (exactly one required)."""
    ru = (registry_uuid or "").strip()
    rn = (registry_name or "").strip()
    if ru and rn:
        return None, f"{prefix}: pass only one of --registry-uuid or --registry-name"
    if not ru and not rn:
        return None, f"{prefix}: --registry-uuid or --registry-name is required"
    if ru:
        if not is_uuid(ru):
            return None, f"{prefix}: invalid --registry-uuid"
        row = con.execute("SELECT uuid FROM registries WHERE uuid = ?", (ru,)).fetchone()
        if not row:
            return None, f"{prefix}: registry not found (--registry-uuid)"
        return row[0], None
    row = con.execute(
        "SELECT uuid FROM registries WHERE LOWER(name) = LOWER(?)",
        (rn,),
    ).fetchone()
    if not row:
        return None, f"{prefix}: registry not found (--registry-name)"
    return row[0], None


def count_uses_for_registry(con: sqlite3.Connection, registry_uuid: str) -> int:
    row = con.execute(
        "SELECT COUNT(*) FROM uses WHERE registry_uuid = ?",
        (registry_uuid,),
    ).fetchone()
    return int(row[0]) if row else 0
