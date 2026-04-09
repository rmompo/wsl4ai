"""Shared business-logic layer — the contract between CLI/TUI consumers and the app.

Every interface_* function executes the business logic and returns a JSON-compatible
``dict`` using the existing envelope format::

    {
        "runtimeId": {"machine": "...", "user": "..."},
        "input":     {"command": "registry", "subcommand": "add", "options": []},
        "output": {
            "result": {"status": 0, "message": "...", "uuid": ""},
            "data":   {"rows": [{"fields": [{"key": "k", "value": "v"}, ...]}]}
        }
    }

The ``options`` list is left empty — CLI consumers fill it from argparse before
printing; TUI consumers ignore it.

Consumers:
    CLI consumer  → fills ``options`` → prints JSON → ``format_envelope_for_cli``
    TUI consumer  → passes envelope to ``tui_decorator.*_records()`` for display
"""

from __future__ import annotations

import logging
import os

_log = logging.getLogger("interface")
import platform
import shutil
import sqlite3
import subprocess
import uuid as _uuid_mod
from pathlib import Path

from commands.api_json import row_from_pairs
from commands.common import (
    DB_PATH,
    TABLE_DDL,
    connect_db,
    expand_path_template,
    load_local_env_paths,
    resolve_runtime_identity,
)
from commands.wsl_db import (
    count_uses_for_registry,
    is_uuid,
    resolve_registry_target,
    resolve_wsl_uuid,
)


# ─── Envelope helpers ─────────────────────────────────────────────────────────

def _envelope(
    command: str,
    subcommand: str,
    status: int,
    message: str,
    *,
    uuid: str = "",
    rows: "list | None" = None,
) -> dict:
    """Build a JSON-compatible envelope dict (same format as emit_envelope output)."""
    ri = resolve_runtime_identity()
    result: dict = {"status": status, "message": message}
    if uuid:
        result["uuid"] = uuid
    return {
        "runtimeId": {"machine": ri.machine, "user": ri.user},
        "input":     {"command": command, "subcommand": subcommand, "options": []},
        "output":    {
            "result": result,
            "data":   {"rows": rows or []},
        },
    }


def _ok(command: str, subcommand: str, message: str, **kw) -> dict:
    return _envelope(command, subcommand, 0, message, **kw)


def _err(command: str, subcommand: str, message: str) -> dict:
    return _envelope(command, subcommand, 1, message)


def _db_missing(command: str, subcommand: str) -> dict:
    return _err(command, subcommand, "database file not found")


def _check_db(command: str, subcommand: str) -> "dict | None":
    if not DB_PATH.is_file():
        return _db_missing(command, subcommand)
    return None


def status_of(envelope: dict) -> int:
    """Extract status code from an envelope dict."""
    return int(envelope.get("output", {}).get("result", {}).get("status", 1))


def message_of(envelope: dict) -> str:
    """Extract message from an envelope dict."""
    return envelope.get("output", {}).get("result", {}).get("message", "")


def rows_of(envelope: dict) -> list:
    """Extract rows list from an envelope dict."""
    return envelope.get("output", {}).get("data", {}).get("rows", [])


def emit_from_interface(
    args,
    envelope: dict,
    opts: list,
    *,
    include_data: "bool | None" = None,
) -> int:
    """CLI Consumer helper: emit an interface envelope as a CLI JSON envelope.

    Patches ``runtimeId`` and ``options`` from *args* and *opts*, then delegates
    to ``emit_envelope`` so the CLI output is identical in format to what the
    previous ``cmd_*`` implementations produced.
    """
    from commands.api_json import emit_envelope
    uuid = envelope.get("output", {}).get("result", {}).get("uuid", "")
    return emit_envelope(
        args=args,
        command=envelope["input"]["command"],
        subcommand=envelope["input"]["subcommand"],
        options=opts,
        status=status_of(envelope),
        message=message_of(envelope),
        uuid=uuid,
        rows=rows_of(envelope),
        include_data=include_data,
    )


# ─── Path helpers ─────────────────────────────────────────────────────────────

def _full_path(base_raw: str, rel: str) -> str:
    root = expand_path_template(base_raw or "")
    return str(Path(os.path.normpath(os.path.join(root, rel))))


def _resolve_full_host_wsl(rel_host: str, rel_wsl: str) -> "tuple[str, str, str]":
    base_host, base_wsl = load_local_env_paths()
    if not base_host:
        return "", "", "missing HOST_PROJECTS in local.env"
    if not base_wsl:
        return "", "", "missing WSL_PROJECTS in local.env"
    host = os.path.normpath(os.path.join(expand_path_template(base_host), rel_host))
    wsl  = os.path.normpath(os.path.join(expand_path_template(base_wsl),  rel_wsl))
    return host, wsl, ""


# ─── Registry ─────────────────────────────────────────────────────────────────

def interface_registry_list() -> dict:
    """SELECT all registries with resolved full paths and in-use indicator."""
    cmd, sub = "registry", "list"
    if e := _check_db(cmd, sub): return e
    try:
        with connect_db(DB_PATH) as con:
            base_host, base_wsl = load_local_env_paths()
            rows_db = con.execute(
                "SELECT uuid, name, rel_path_host, rel_path_wsl FROM registries ORDER BY name COLLATE NOCASE"
            ).fetchall()
            if not rows_db:
                return _ok(cmd, sub, "no registry entries")
            rows = []
            for reg_uuid, name, h_rel, w_rel in rows_db:
                in_use = con.execute(
                    "SELECT 1 FROM uses WHERE registry_uuid = ? LIMIT 1", (reg_uuid,)
                ).fetchone()
                rows.append(row_from_pairs([
                    ("registryUuid", reg_uuid),
                    ("registryName", name),
                    ("hostPath",     _full_path(base_host, h_rel)),
                    ("wslPath",      _full_path(base_wsl,  w_rel)),
                    ("inUse",        "true" if in_use else "false"),
                ]))
        return _ok(cmd, sub, f"listed {len(rows)} registry(ies)", rows=rows)
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def interface_registry_list_available(wsl_name: str, user: str) -> dict:
    """Registries NOT yet linked to the given WSL (for Use > Add)."""
    cmd, sub = "registry", "list-available"
    if e := _check_db(cmd, sub): return e
    try:
        with connect_db(DB_PATH) as con:
            base_host, base_wsl = load_local_env_paths()
            rows_db = con.execute(
                """
                SELECT r.uuid, r.name, r.rel_path_host, r.rel_path_wsl
                FROM registries r
                WHERE NOT EXISTS (
                    SELECT 1 FROM uses u JOIN wsls w ON w.uuid = u.wsl_uuid
                    WHERE u.registry_uuid = r.uuid AND w.name = ? AND w.user = ?
                )
                ORDER BY r.name COLLATE NOCASE
                """,
                (wsl_name, user),
            ).fetchall()
        if not rows_db:
            return _ok(cmd, sub, "no registries available")
        rows = [
            row_from_pairs([
                ("registryUuid", r[0]),
                ("registryName", r[1]),
                ("hostPath",     _full_path(base_host, r[2])),
                ("wslPath",      _full_path(base_wsl,  r[3])),
            ])
            for r in rows_db
        ]
        return _ok(cmd, sub, f"listed {len(rows)} available registry(ies)", rows=rows)
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def interface_registry_add(
    name: str,
    host_rel: str,
    wsl_rel: str,
    *,
    force: bool = False,
) -> dict:
    """Validate paths + INSERT into registries."""
    cmd, sub = "registry", "add"
    if e := _check_db(cmd, sub): return e
    name, host_rel, wsl_rel = name.strip(), host_rel.strip(), wsl_rel.strip()
    if not name or not host_rel or not wsl_rel:
        return _err(cmd, sub, "add: name, host and wsl must be non-empty")
    if not force:
        host_base, _ = load_local_env_paths()
        if not host_base:
            return _err(cmd, sub, "add: missing HOST_PROJECTS in local.env")
        host_full = Path(os.path.normpath(
            os.path.join(expand_path_template(host_base), host_rel)
        ))
        if not host_full.exists():
            return _err(cmd, sub, f"add: host path not found: {host_full}")
    uid = str(_uuid_mod.uuid4())
    try:
        with connect_db(DB_PATH) as con:
            taken = con.execute(
                "SELECT name FROM registries WHERE LOWER(name) = LOWER(?) LIMIT 1", (name,)
            ).fetchone()
            if taken:
                return _err(cmd, sub, f"add: name already taken ({taken[0]!r})")
            con.execute(
                "INSERT INTO registries (uuid, name, rel_path_host, rel_path_wsl) VALUES (?,?,?,?)",
                (uid, name, host_rel, wsl_rel),
            )
    except sqlite3.IntegrityError:
        return _err(cmd, sub, "add: insert rejected (duplicate name?)")
    except Exception as exc:
        return _err(cmd, sub, str(exc))
    return _ok(cmd, sub, f"registry entry added: {name}",
               uuid=uid,
               rows=[row_from_pairs([("registryUuid", uid), ("registryName", name)])])


def interface_registry_remove(
    *,
    registry_uuid: str = "",
    registry_name: str = "",
) -> dict:
    """Validate (no use links) + DELETE from registries."""
    cmd, sub = "registry", "remove"
    if e := _check_db(cmd, sub): return e
    reg_uuid, reg_name = registry_uuid.strip(), registry_name.strip()
    if not reg_uuid and not reg_name:
        return _err(cmd, sub, "remove: registry_uuid or registry_name is required")
    try:
        with connect_db(DB_PATH) as con:
            if reg_uuid:
                if not is_uuid(reg_uuid):
                    return _err(cmd, sub, f"remove: invalid uuid: {reg_uuid!r}")
                row = con.execute(
                    "SELECT uuid, name FROM registries WHERE uuid = ?", (reg_uuid,)
                ).fetchone()
            else:
                row = con.execute(
                    "SELECT uuid, name FROM registries WHERE LOWER(name) = LOWER(?)", (reg_name,)
                ).fetchone()
            if not row:
                key = f"uuid={reg_uuid!r}" if reg_uuid else f"name={reg_name!r}"
                return _err(cmd, sub, f"remove: not found ({key})")
            rid, rname = row
            if count_uses_for_registry(con, rid) > 0:
                return _err(cmd, sub,
                            "remove: registry still has use links; run 'use disable' + 'use remove' first")
            con.execute("DELETE FROM registries WHERE uuid = ?", (rid,))
    except Exception as exc:
        return _err(cmd, sub, str(exc))
    return _ok(cmd, sub, f"removed registry: {rname}",
               rows=[row_from_pairs([("registryUuid", rid), ("registryName", rname)])])


# ─── Use ──────────────────────────────────────────────────────────────────────

def interface_use_list(
    *,
    wsl_uuid: str = "",
    wsl_name: str = "",
    user: str = "",
    runtime_wsl_name: str = "",
    use_all: bool = False,
    mounted_filter: "int | None" = None,
) -> dict:
    """SELECT uses — covers use list, use list filtered by mounted state."""
    cmd, sub = "use", "list"
    if e := _check_db(cmd, sub): return e
    if not user or not runtime_wsl_name:
        ri = resolve_runtime_identity()
        user = user or ri.user
        runtime_wsl_name = runtime_wsl_name or ri.wsl_name
    try:
        with connect_db(DB_PATH) as con:
            where_parts: list[str] = []
            params: list = []
            if not use_all:
                wsl_id, err_w = resolve_wsl_uuid(
                    con,
                    wsl_uuid=wsl_uuid,
                    wsl_name=wsl_name,
                    runtime_user=user,
                    runtime_wsl_name=runtime_wsl_name,
                    create_if_missing=False,
                )
                if err_w:
                    return _err(cmd, sub, err_w)
                where_parts.append("u.wsl_uuid = ?")
                params.append(wsl_id)
            if mounted_filter is not None:
                where_parts.append("u.mounted = ?")
                params.append(mounted_filter)
            where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
            rows_db = con.execute(
                f"""
                SELECT u.wsl_uuid, w.name, w.user, u.registry_uuid, r.name, u.mounted
                FROM uses u
                JOIN wsls w ON w.uuid = u.wsl_uuid
                JOIN registries r ON r.uuid = u.registry_uuid
                {where_sql}
                ORDER BY w.name COLLATE NOCASE, w.user COLLATE NOCASE, r.name COLLATE NOCASE
                """,
                params,
            ).fetchall()
        if not rows_db:
            return _ok(cmd, sub, "no usage links found")
        rows = [
            row_from_pairs([
                ("wslUuid",      r[0]),
                ("wslName",      r[1]),
                ("wslUser",      r[2]),
                ("registryUuid", r[3]),
                ("registryName", r[4]),
                ("mounted",      str(int(r[5]))),
            ])
            for r in rows_db
        ]
        return _ok(cmd, sub, f"listed {len(rows)} usage link(s)", rows=rows)
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def interface_use_list_mounted(wsl_name: str, user: str) -> dict:
    """SELECT mounted=1 uses for the given WSL including full paths and cli_command.

    ``envelope["output"]["data"]["raw_rows"]`` contains raw DB tuples
    ``(r_uuid, r_name, rel_path_host, rel_path_wsl, cli_cmd)`` for StartDialog.
    """
    cmd, sub = "use", "list-mounted"
    if e := _check_db(cmd, sub): return e
    try:
        with connect_db(DB_PATH) as con:
            rows_db = con.execute(
                """
                SELECT r.uuid, r.name, r.rel_path_host, r.rel_path_wsl, w.cli_command
                FROM uses u
                JOIN registries r ON r.uuid = u.registry_uuid
                JOIN wsls w ON w.uuid = u.wsl_uuid
                WHERE u.mounted = 1 AND w.name = ? AND w.user = ?
                ORDER BY r.name COLLATE NOCASE
                """,
                (wsl_name, user),
            ).fetchall()
        if not rows_db:
            return _ok(cmd, sub, "no mounted uses")
        base_host, base_wsl = load_local_env_paths()
        rows = [
            row_from_pairs([
                ("registryUuid", r[0]),
                ("registryName", r[1]),
                ("hostPath",     _full_path(base_host, r[2])),
                ("wslPath",      _full_path(base_wsl,  r[3])),
            ])
            for r in rows_db
        ]
        envelope = _ok(cmd, sub, f"listed {len(rows)} mounted use(s)", rows=rows)
        # Attach raw rows for StartDialog (TUI-only, not part of JSON wire format)
        envelope["output"]["data"]["raw_rows"] = list(rows_db)
        return envelope
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def interface_use_add(
    registry_uuid: str,
    *,
    wsl_uuid: str = "",
    wsl_name: str = "",
    user: str = "",
    runtime_wsl_name: str = "",
) -> dict:
    """Resolve WSL + INSERT into uses + create WSL directory."""
    cmd, sub = "use", "add"
    if e := _check_db(cmd, sub): return e
    if not user or not runtime_wsl_name:
        ri = resolve_runtime_identity()
        user = user or ri.user
        runtime_wsl_name = runtime_wsl_name or ri.wsl_name
    try:
        with connect_db(DB_PATH) as con:
            reg_id, err_r = resolve_registry_target(
                con, registry_uuid=registry_uuid, registry_name=""
            )
            if err_r:
                return _err(cmd, sub, err_r)
            wsl_id, err_w = resolve_wsl_uuid(
                con,
                wsl_uuid=wsl_uuid,
                wsl_name=wsl_name,
                runtime_user=user,
                runtime_wsl_name=runtime_wsl_name,
                create_if_missing=True,
            )
            if err_w:
                return _err(cmd, sub, err_w)
            if con.execute(
                "SELECT 1 FROM uses WHERE wsl_uuid = ? AND registry_uuid = ?",
                (wsl_id, reg_id),
            ).fetchone():
                return _err(cmd, sub, "use add: link already exists for this wsl and registry")
            rel_wsl_row = con.execute(
                "SELECT rel_path_wsl FROM registries WHERE uuid = ?", (reg_id,)
            ).fetchone()
            if rel_wsl_row:
                _, wsl_root = load_local_env_paths()
                if wsl_root:
                    wsl_full = os.path.normpath(
                        os.path.join(expand_path_template(wsl_root), rel_wsl_row[0])
                    )
                    try:
                        os.makedirs(wsl_full, exist_ok=True)
                    except OSError as exc:
                        return _err(cmd, sub,
                                    f"use add: could not create wsl path {wsl_full}: {exc}")
            con.execute(
                "INSERT INTO uses (wsl_uuid, registry_uuid, mounted) VALUES (?, ?, 0)",
                (wsl_id, reg_id),
            )
        return _ok(cmd, sub, "use add: link created",
                   rows=[row_from_pairs([("wslUuid", wsl_id), ("registryUuid", reg_id), ("mounted", "0")])])
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def _resolve_pair(
    con,
    cmd: str,
    sub: str,
    registry_uuid: str,
    registry_name: str,
    wsl_uuid: str,
    wsl_name: str,
    user: str,
    runtime_wsl_name: str,
) -> "tuple[str, str, dict | None]":
    """Resolve (registry_uuid, wsl_uuid) from names if needed.  Returns (reg_id, wsl_id, error_envelope)."""
    reg_id, err_r = resolve_registry_target(
        con, registry_uuid=registry_uuid, registry_name=registry_name
    )
    if err_r:
        return "", "", _err(cmd, sub, err_r)
    if not wsl_uuid and not wsl_name:
        return reg_id, "", _err(cmd, sub, f"{sub}: wsl_uuid or wsl_name is required")
    wsl_id, err_w = resolve_wsl_uuid(
        con,
        wsl_uuid=wsl_uuid,
        wsl_name=wsl_name,
        runtime_user=user,
        runtime_wsl_name=runtime_wsl_name,
        create_if_missing=False,
    )
    if err_w:
        return reg_id, "", _err(cmd, sub, err_w)
    return reg_id, wsl_id, None


def interface_use_remove(
    registry_uuid: str,
    wsl_uuid: str,
    *,
    registry_name: str = "",
    wsl_name: str = "",
    user: str = "",
    runtime_wsl_name: str = "",
) -> dict:
    """Validate (not mounted) + DELETE from uses + remove WSL directory."""
    cmd, sub = "use", "remove"
    if e := _check_db(cmd, sub): return e
    if not user or not runtime_wsl_name:
        ri = resolve_runtime_identity()
        user = user or ri.user
        runtime_wsl_name = runtime_wsl_name or ri.wsl_name
    try:
        with connect_db(DB_PATH) as con:
            reg_id, wsl_id, err_env = _resolve_pair(
                con, cmd, sub, registry_uuid, registry_name, wsl_uuid, wsl_name, user, runtime_wsl_name
            )
            if err_env is not None:
                return err_env
            row = con.execute(
                "SELECT u.mounted, r.rel_path_wsl FROM uses u "
                "JOIN registries r ON r.uuid = u.registry_uuid "
                "WHERE u.wsl_uuid = ? AND u.registry_uuid = ?",
                (wsl_id, reg_id),
            ).fetchone()
            if not row:
                return _err(cmd, sub, "use remove: link not found")
            if int(row[0]) != 0:
                return _err(cmd, sub, "use remove: mounted=1; use disable first")
            rel_wsl = row[1]
            _, wsl_root = load_local_env_paths()
            if wsl_root and rel_wsl:
                wsl_full = os.path.normpath(
                    os.path.join(expand_path_template(wsl_root), rel_wsl)
                )
                try:
                    shutil.rmtree(wsl_full)
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    return _err(cmd, sub,
                                f"use remove: could not remove directory {wsl_full}: {exc}")
            con.execute(
                "DELETE FROM uses WHERE wsl_uuid = ? AND registry_uuid = ?",
                (wsl_id, reg_id),
            )
        return _ok(cmd, sub, "use remove: link removed",
                   rows=[row_from_pairs([("wslUuid", wsl_id), ("registryUuid", reg_id)])])
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def interface_use_enable(
    registry_uuid: str,
    wsl_uuid: str,
    *,
    registry_name: str = "",
    wsl_name: str = "",
    user: str = "",
    runtime_wsl_name: str = "",
) -> dict:
    """Resolve paths + sudo mount --bind + UPDATE uses SET mounted=1."""
    cmd, sub = "use", "enable"
    if e := _check_db(cmd, sub): return e
    if not user or not runtime_wsl_name:
        ri = resolve_runtime_identity()
        user = user or ri.user
        runtime_wsl_name = runtime_wsl_name or ri.wsl_name
    try:
        with connect_db(DB_PATH) as con:
            reg_id, wsl_id, err_env = _resolve_pair(
                con, cmd, sub, registry_uuid, registry_name, wsl_uuid, wsl_name, user, runtime_wsl_name
            )
            if err_env is not None:
                return err_env
            row = con.execute(
                "SELECT u.mounted, r.rel_path_host, r.rel_path_wsl FROM uses u "
                "JOIN registries r ON r.uuid = u.registry_uuid "
                "WHERE u.wsl_uuid = ? AND u.registry_uuid = ?",
                (wsl_id, reg_id),
            ).fetchone()
            if not row:
                return _err(cmd, sub, "use enable: link not found")
            if int(row[0]) == 1:
                return _err(cmd, sub, "use enable: already mounted")
            rel_host, rel_wsl = row[1], row[2]

        host_path, wsl_path, path_err = _resolve_full_host_wsl(rel_host, rel_wsl)
        if path_err:
            return _err(cmd, sub, f"use enable: {path_err}")

        _log.debug("use enable: host=%s wsl=%s", host_path, wsl_path)

        if not os.path.isdir(host_path):
            return _err(cmd, sub, f"use enable: host path not found: {host_path}")

        try:
            os.makedirs(wsl_path, exist_ok=True)
        except OSError as exc:
            return _err(cmd, sub, f"use enable: could not create wsl path {wsl_path}: {exc}")

        try:
            result = subprocess.run(
                ["sudo", "mount", "--bind", host_path, wsl_path],
                check=True, capture_output=True,
            )
            _log.debug("use enable: mount ok stdout=%s", result.stdout.decode().strip())
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode().strip() if exc.stderr else str(exc)
            _log.error("use enable: mount failed: %s", stderr)
            return _err(cmd, sub, f"use enable: mount failed: {stderr}")

        with connect_db(DB_PATH) as con:
            con.execute(
                "UPDATE uses SET mounted = 1 WHERE wsl_uuid = ? AND registry_uuid = ?",
                (wsl_id, reg_id),
            )
        return _ok(cmd, sub, f"use enable: mounted {wsl_path}",
                   rows=[row_from_pairs([
                       ("wslUuid",      wsl_id),
                       ("registryUuid", reg_id),
                       ("mounted",      "1"),
                       ("wslPath",      wsl_path),
                   ])])
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def interface_use_disable(
    registry_uuid: str,
    wsl_uuid: str,
    *,
    registry_name: str = "",
    wsl_name: str = "",
    user: str = "",
    runtime_wsl_name: str = "",
) -> dict:
    """sudo umount + UPDATE uses SET mounted=0."""
    cmd, sub = "use", "disable"
    if e := _check_db(cmd, sub): return e
    if not user or not runtime_wsl_name:
        ri = resolve_runtime_identity()
        user = user or ri.user
        runtime_wsl_name = runtime_wsl_name or ri.wsl_name
    try:
        with connect_db(DB_PATH) as con:
            reg_id, wsl_id, err_env = _resolve_pair(
                con, cmd, sub, registry_uuid, registry_name, wsl_uuid, wsl_name, user, runtime_wsl_name
            )
            if err_env is not None:
                return err_env
            row = con.execute(
                "SELECT u.mounted, r.rel_path_host, r.rel_path_wsl FROM uses u "
                "JOIN registries r ON r.uuid = u.registry_uuid "
                "WHERE u.wsl_uuid = ? AND u.registry_uuid = ?",
                (wsl_id, reg_id),
            ).fetchone()
            if not row:
                return _err(cmd, sub, "use disable: link not found")
            if int(row[0]) == 0:
                return _err(cmd, sub, "use disable: not mounted")
            rel_host, rel_wsl = row[1], row[2]

        _, wsl_path, path_err = _resolve_full_host_wsl(rel_host, rel_wsl)
        if path_err:
            return _err(cmd, sub, f"use disable: {path_err}")

        _log.debug("use disable: wsl=%s", wsl_path)
        umount_err = None
        try:
            subprocess.run(["sudo", "umount", wsl_path], check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            umount_err = exc.stderr.decode().strip() if exc.stderr else str(exc)
            _log.error("use disable: umount failed: %s", umount_err)

        with connect_db(DB_PATH) as con:
            con.execute(
                "UPDATE uses SET mounted = 0 WHERE wsl_uuid = ? AND registry_uuid = ?",
                (wsl_id, reg_id),
            )

        if umount_err:
            return _err(cmd, sub, f"use disable: umount failed (state reset to 0): {umount_err}")
        return _ok(cmd, sub, f"use disable: unmounted {wsl_path}",
                   rows=[row_from_pairs([
                       ("wslUuid",      wsl_id),
                       ("registryUuid", reg_id),
                       ("mounted",      "0"),
                   ])])
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def interface_use_disableall(
    *,
    wsl_uuid: str = "",
    wsl_name: str = "",
    user: str = "",
    runtime_wsl_name: str = "",
) -> dict:
    """Disable all mounted uses for the given WSL."""
    cmd, sub = "use", "disableall"
    if e := _check_db(cmd, sub): return e
    if not user or not runtime_wsl_name:
        ri = resolve_runtime_identity()
        user = user or ri.user
        runtime_wsl_name = runtime_wsl_name or ri.wsl_name
    try:
        with connect_db(DB_PATH) as con:
            wsl_id, err_w = resolve_wsl_uuid(
                con,
                wsl_uuid=wsl_uuid,
                wsl_name=wsl_name,
                runtime_user=user,
                runtime_wsl_name=runtime_wsl_name,
                create_if_missing=False,
            )
            if err_w:
                return _err(cmd, sub, err_w)
            mounted = con.execute(
                """
                SELECT u.registry_uuid, r.rel_path_host, r.rel_path_wsl
                FROM uses u JOIN registries r ON r.uuid = u.registry_uuid
                WHERE u.wsl_uuid = ? AND u.mounted = 1
                """,
                (wsl_id,),
            ).fetchall()
        errors = []
        disabled_rows = []
        for reg_id, _, _ in mounted:
            res = interface_use_disable(reg_id, wsl_id)
            if status_of(res) == 0:
                disabled_rows.append(
                    row_from_pairs([("wslUuid", wsl_id), ("registryUuid", reg_id), ("mounted", "0")])
                )
            else:
                errors.append(message_of(res))
        if errors:
            return _err(cmd, sub,
                        f"use disableall: {len(disabled_rows)} disabled, {len(errors)} failed: {'; '.join(errors)}")
        return _ok(cmd, sub, f"use disableall: {len(disabled_rows)} use(s) disabled",
                   rows=disabled_rows)
    except Exception as exc:
        return _err(cmd, sub, str(exc))


# ─── WSL ──────────────────────────────────────────────────────────────────────

def interface_wsl_list() -> dict:
    """SELECT all wsls rows."""
    cmd, sub = "wsl", "list"
    if e := _check_db(cmd, sub): return e
    try:
        with connect_db(DB_PATH) as con:
            rows_db = con.execute(
                "SELECT uuid, name, user, cli_command FROM wsls "
                "ORDER BY name COLLATE NOCASE, user COLLATE NOCASE"
            ).fetchall()
        if not rows_db:
            return _ok(cmd, sub, "no WSL rows found")
        rows = [
            row_from_pairs([
                ("wslUuid",    r[0]),
                ("wslName",    r[1]),
                ("wslUser",    r[2]),
                ("cliCommand", (r[3] or "").strip() or "<unset>"),
            ])
            for r in rows_db
        ]
        return _ok(cmd, sub, f"listed {len(rows)} WSL row(s)", rows=rows)
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def interface_wsl_set(
    cli_command: str,
    *,
    wsl_uuid: str = "",
    wsl_name: str = "",
    user: str = "",
    runtime_wsl_name: str = "",
) -> dict:
    """Validate + UPDATE wsls SET cli_command."""
    cmd, sub = "wsl", "set"
    if e := _check_db(cmd, sub): return e
    cli_command = cli_command.strip()
    if not cli_command:
        return _err(cmd, sub, "wsl set: cli_command must be non-empty")
    if not user or not runtime_wsl_name:
        ri = resolve_runtime_identity()
        user = user or ri.user
        runtime_wsl_name = runtime_wsl_name or ri.wsl_name
    try:
        with connect_db(DB_PATH) as con:
            wsl_id, err_w = resolve_wsl_uuid(
                con,
                wsl_uuid=wsl_uuid,
                wsl_name=wsl_name,
                runtime_user=user,
                runtime_wsl_name=runtime_wsl_name,
                create_if_missing=False,
                msg_prefix="wsl set",
            )
            if err_w:
                return _err(cmd, sub, err_w)
            con.execute(
                "UPDATE wsls SET cli_command = ? WHERE uuid = ?", (cli_command, wsl_id)
            )
        return _ok(cmd, sub, "wsl set: cli_command updated",
                   rows=[row_from_pairs([("wslUuid", wsl_id), ("cliCommand", cli_command)])])
    except Exception as exc:
        return _err(cmd, sub, str(exc))


# ─── Install ──────────────────────────────────────────────────────────────────

def interface_install_database(*, force: bool = False) -> dict:
    """Create (or recreate if force) ddbb/wsl4ai.db."""
    cmd, sub = "install", "database"
    script_dir = Path(__file__).resolve().parent.parent
    ddbb_dir = script_dir.parent / "conf" / "ddbb"
    db_path = ddbb_dir / "wsl4ai.db"
    ddbb_dir.mkdir(parents=True, exist_ok=True)
    if db_path.is_file() and not force:
        return _ok(cmd, sub, f"database already exists: {db_path}")
    if db_path.is_file() and force:
        db_path.unlink()
    try:
        con = connect_db(db_path)
        con.executescript(TABLE_DDL)
        con.commit()
        con.close()
    except Exception as exc:
        return _err(cmd, sub, str(exc))
    return _ok(cmd, sub, "database created" if not force else "database recreated")


def interface_alias_list() -> dict:
    """List current aliases from shell profile files."""
    cmd, sub = "install", "alias"
    shell_type = "ps" if platform.system() == "Windows" else "bash"
    from commands.alias_bash import BASH_BEGIN, BASH_END, bashrc_path
    from commands.install_alias import _bash_names_from_block, _extract_block
    rows = []
    try:
        if shell_type == "ps":
            from commands.alias_ps import PS_BEGIN, PS_END, profile_paths
            from commands.install_alias import _ps_names_from_block
            for path in profile_paths():
                content = path.read_text(encoding="utf-8") if path.exists() else ""
                _, block, _ = _extract_block(content, PS_BEGIN, PS_END)
                for name in _ps_names_from_block(block):
                    rows.append(row_from_pairs([("type", "ps"), ("name", name)]))
        else:
            path = bashrc_path()
            content = path.read_text(encoding="utf-8") if path.exists() else ""
            _, block, _ = _extract_block(content, BASH_BEGIN, BASH_END)
            for name in _bash_names_from_block(block):
                rows.append(row_from_pairs([("type", "bash"), ("name", name)]))
        return _ok(cmd, sub, "install alias: list completed", rows=rows)
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def _alias_mutate(action: str, names: list[str]) -> dict:
    """Shared implementation for alias add and remove."""
    cmd, sub = "install", "alias"
    shell_type = "ps" if platform.system() == "Windows" else "bash"
    from commands.alias_bash import BASH_BEGIN, BASH_END, bashrc_path
    from commands.install_alias import (
        _bash_names_from_block, _build_bash_block, _extract_block, _script_and_python,
    )
    script_path, python_exe = _script_and_python()
    names = [n.strip() for n in names if n.strip()]
    rows = []
    failures = 0
    try:
        if shell_type == "ps":
            from commands.alias_ps import PS_BEGIN, PS_END, profile_paths
            from commands.install_alias import _build_ps_block, _ps_names_from_block
            targets = profile_paths()
            begin, end = PS_BEGIN, PS_END
            names_fn = _ps_names_from_block
            build_fn = lambda ns: _build_ps_block(ns, script_path, python_exe)
        else:
            targets = [bashrc_path()]
            begin, end = BASH_BEGIN, BASH_END
            names_fn = _bash_names_from_block
            build_fn = lambda ns: _build_bash_block(ns, script_path, python_exe)

        profile_state = []
        for target in targets:
            if action == "add":
                target.parent.mkdir(parents=True, exist_ok=True)
            content = target.read_text(encoding="utf-8") if target.exists() else ""
            _, block, _ = _extract_block(content, begin, end)
            profile_state.append((target, content, names_fn(block)))

        status_by_name: dict[str, str] = {}
        to_mutate: list[str] = []
        for name in dict.fromkeys(names):
            exists = any(name in curr for _, _, curr in profile_state)
            if action == "add":
                if exists:
                    status_by_name[name] = "error_exists"
                else:
                    status_by_name[name] = "added"
                    to_mutate.append(name)
            else:
                if exists:
                    status_by_name[name] = "removed"
                    to_mutate.append(name)
                else:
                    status_by_name[name] = "error_not_found"

        for target, content, curr_names in profile_state:
            if action == "add":
                effective = list(curr_names) + [n for n in to_mutate if n not in curr_names]
            else:
                effective = [n for n in curr_names if n not in to_mutate]
            before, _, after = _extract_block(content, begin, end)
            if not effective:
                updated = before
                if after:
                    updated = (updated + "\n\n" + after) if updated else after
                updated = updated.rstrip() + ("\n" if updated else "")
            else:
                updated = before + ("\n\n" if before else "") + build_fn(effective)
                if after:
                    updated += ("\n" if not updated.endswith("\n") else "") + "\n" + after
            target.write_text(updated, encoding="utf-8")

        for name in dict.fromkeys(names):
            st = status_by_name.get(name, "error_unknown")
            if st.startswith("error_"):
                failures += 1
            rows.append(row_from_pairs([
                ("type", shell_type), ("name", name), ("action", action), ("status", st)
            ]))

        status = 1 if failures else 0
        msg = "install alias: completed" if not failures else "install alias: one or more aliases failed"
        return _envelope(cmd, sub, status, msg, rows=rows)
    except Exception as exc:
        return _err(cmd, sub, str(exc))


def interface_alias_add(names: list[str]) -> dict:
    """Add aliases to shell profile files."""
    return _alias_mutate("add", names)


def interface_alias_remove(names: list[str]) -> dict:
    """Remove aliases from shell profile files."""
    return _alias_mutate("remove", names)


# ─── Whoami ───────────────────────────────────────────────────────────────────

def interface_whoami() -> dict:
    """Return machine/user/wsl_name from runtime identity."""
    ri = resolve_runtime_identity()
    return _ok("whoami", "", "runtime identity",
               rows=[row_from_pairs([("machine", ri.machine), ("user", ri.user), ("wslName", ri.wsl_name)])])


# ─── Start (validation only) ──────────────────────────────────────────────────

def interface_start_prepare(wsl_name: str, user: str) -> dict:
    """Validate that the current WSL has a cli_command set.

    On success: ``status=0``, ``envelope["output"]["data"]["cli_command"]`` is set.
    On failure: ``status=1`` with an error message.
    """
    cmd, sub = "start", "prepare"
    if e := _check_db(cmd, sub): return e
    try:
        with connect_db(DB_PATH) as con:
            row = con.execute(
                "SELECT cli_command FROM wsls WHERE name = ? AND user = ?",
                (wsl_name, user),
            ).fetchone()
        if not row:
            return _err(cmd, sub, f"WSL '{wsl_name}' not found in DB — run 'use add' first")
        cli_command = (row[0] or "").strip()
        if not cli_command:
            return _err(cmd, sub, "No CLI command set — configure it via Wsl > Set")
        envelope = _ok(cmd, sub, "WSL ready")
        envelope["output"]["data"]["cli_command"] = cli_command
        return envelope
    except Exception as exc:
        return _err(cmd, sub, str(exc))
