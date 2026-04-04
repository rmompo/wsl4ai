"""Add and remove registry rows only."""

import os
import re
import sqlite3
import uuid
from argparse import Namespace, _SubParsersAction
from pathlib import Path

from commands.api_json import OptionSpec, emit_envelope, options_from_args, row_from_pairs
from commands.common import DB_PATH, connect_db, expand_path_template, load_local_env_paths, require_database_file
from commands.help_md import help_summary_for_root, parser_description_from_manual
from commands.wsl_db import count_uses_for_registry

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _is_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value.strip()))


def _registry_row_by_uuid(con: sqlite3.Connection, reg_uuid: str) -> tuple[str, str, str, str] | None:
    row = con.execute(
        "SELECT uuid, name, rel_path_host, rel_path_wsl FROM registries WHERE uuid = ?",
        (reg_uuid.strip(),),
    ).fetchone()
    return row


def _registry_row_by_name(con: sqlite3.Connection, name: str) -> tuple[str, str, str, str] | None:
    row = con.execute(
        "SELECT uuid, name, rel_path_host, rel_path_wsl FROM registries WHERE LOWER(name) = LOWER(?)",
        (name.strip(),),
    ).fetchone()
    return row


def _absolute_under_param(base_raw: str, rel_segment: str) -> Path:
    """Join expanded base with relative segment using ``os.path.join`` (no manual slash)."""
    root = expand_path_template(base_raw)
    rel = rel_segment.strip()
    return Path(os.path.normpath(os.path.join(root, rel)))


def _paths_under_param_exist(host_rel: str, wsl_rel: str) -> tuple[bool, str]:
    """Ensure paths under HOST_PROJECTS and WSL_PROJECTS from local.env exist on disk."""
    host_root, wsl_root = load_local_env_paths()
    if not host_root:
        return False, "add: missing HOST_PROJECTS in local.env"
    if not wsl_root:
        return False, "add: missing WSL_PROJECTS in local.env"
    host_full = _absolute_under_param(host_root, host_rel)
    wsl_full = _absolute_under_param(wsl_root, wsl_rel)
    if not host_full.exists():
        return False, f"add: host path not found: {host_full}"
    if not wsl_full.exists():
        return False, f"add: wsl path not found: {wsl_full}"
    return True, ""


def cmd_add(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--name", "name"),
            OptionSpec("--host", "host"),
            OptionSpec("--wsl", "wsl"),
            OptionSpec("--force", "force", is_flag=True),
        ],
    )
    if not require_database_file():
        return emit_envelope(
            args=args,
            command="registry",
            subcommand="add",
            options=opts,
            status=1,
            message="database file not found",
        )
    name = (args.name or "").strip()
    host_rel = (args.host or "").strip()
    wsl_rel = (args.wsl or "").strip()
    if not name or not host_rel or not wsl_rel:
        return emit_envelope(
            args=args,
            command="registry",
            subcommand="add",
            options=opts,
            status=1,
            message="add: --name, --host and --wsl must be non-empty",
        )
    if not getattr(args, "force", False):
        ok_paths, err_paths = _paths_under_param_exist(host_rel, wsl_rel)
        if not ok_paths:
            return emit_envelope(
                args=args,
                command="registry",
                subcommand="add",
                options=opts,
                status=1,
                message=err_paths,
            )
    uid = _new_uuid()
    try:
        with connect_db(DB_PATH) as con:
            taken = con.execute(
                "SELECT name FROM registries WHERE LOWER(name) = LOWER(?) LIMIT 1",
                (name,),
            ).fetchone()
            if taken:
                return emit_envelope(
                    args=args,
                    command="registry",
                    subcommand="add",
                    options=opts,
                    status=1,
                    message=f"add: name already taken ({taken[0]!r})",
                )
            con.execute(
                """
                INSERT INTO registries (uuid, name, rel_path_host, rel_path_wsl)
                VALUES (?, ?, ?, ?)
                """,
                (uid, name, host_rel, wsl_rel),
            )
    except sqlite3.IntegrityError:
        return emit_envelope(
            args=args,
            command="registry",
            subcommand="add",
            options=opts,
            status=1,
            message="add: insert rejected (duplicate name?)",
        )
    return emit_envelope(
        args=args,
        command="registry",
        subcommand="add",
        options=opts,
        status=0,
        message=f"registry entry added: {name}",
        uuid=uid,
        rows=[row_from_pairs([("registryUuid", uid), ("registryName", name)])],
    )


def cmd_remove(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--uuid", "remove_uuid"),
            OptionSpec("--name", "remove_name"),
        ],
    )
    if not require_database_file():
        return emit_envelope(
            args=args,
            command="registry",
            subcommand="remove",
            options=opts,
            status=1,
            message="database file not found",
        )
    reg_uuid = (getattr(args, "remove_uuid", None) or "").strip()
    reg_name = (getattr(args, "remove_name", None) or "").strip()
    if not reg_uuid and not reg_name:
        return emit_envelope(
            args=args,
            command="registry",
            subcommand="remove",
            options=opts,
            status=1,
            message="remove: at least one of --uuid or --name is required",
        )
    with connect_db(DB_PATH) as con:
        if reg_uuid:
            if not _is_uuid(reg_uuid):
                return emit_envelope(
                    args=args,
                    command="registry",
                    subcommand="remove",
                    options=opts,
                    status=1,
                    message=f"remove: invalid uuid: {reg_uuid!r}",
                )
            row = _registry_row_by_uuid(con, reg_uuid)
            if not row:
                return emit_envelope(
                    args=args,
                    command="registry",
                    subcommand="remove",
                    options=opts,
                    status=1,
                    message=f"remove: not found (uuid={reg_uuid!r})",
                )
        else:
            row = _registry_row_by_name(con, reg_name)
            if not row:
                return emit_envelope(
                    args=args,
                    command="registry",
                    subcommand="remove",
                    options=opts,
                    status=1,
                    message=f"remove: not found (name={reg_name!r})",
                )
        rid, rname = row[0], row[1]
        n_use = count_uses_for_registry(con, rid)
        if n_use > 0:
            return emit_envelope(
                args=args,
                command="registry",
                subcommand="remove",
                options=opts,
                status=1,
                message="remove: registry still has use links; run 'use disable' + 'use remove' first",
            )
        con.execute("DELETE FROM registries WHERE uuid = ?", (rid,))
    return emit_envelope(
        args=args,
        command="registry",
        subcommand="remove",
        options=opts,
        status=0,
        message=f"removed registry: {rname}",
        rows=[row_from_pairs([("registryUuid", rid), ("registryName", rname)])],
    )


def register_add_command(
    subparsers: _SubParsersAction,
    *,
    name: str = "add",
    aliases: tuple[str, ...] = (),
    help_override: str | None = None,
) -> None:
    fb = "Register a new mount definition (name plus host and WSL path segments)."
    desc = parser_description_from_manual("registry add", fb)
    if help_override:
        help_line = help_override
    else:
        help_line = help_summary_for_root("registry add", "Add a mount definition")
    add = subparsers.add_parser(
        name,
        aliases=list(aliases),
        help=help_line,
        description=desc,
    )
    base_host, base_wsl = load_local_env_paths()
    host_base_hint = base_host if base_host else "(HOST_PROJECTS not set)"
    wsl_base_hint = base_wsl if base_wsl else "(WSL_PROJECTS not set)"

    req = add.add_argument_group("required arguments")
    req.add_argument("-n", "--name", dest="name", required=True, help="Name for this mount definition")
    req.add_argument(
        "-H",
        "--host",
        dest="host",
        required=True,
        help=f"Host-side folder segment appended to HOST_PROJECTS ({host_base_hint})",
    )
    req.add_argument(
        "-w",
        "--wsl",
        dest="wsl",
        required=True,
        help=f"WSL-side folder segment appended to WSL_PROJECTS ({wsl_base_hint})",
    )
    add.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Proceed when folder paths are not ready yet",
    )
    # Show required flags before optional (--force, --help)
    if req in add._action_groups and add._optionals in add._action_groups:
        add._action_groups.remove(req)
        idx = add._action_groups.index(add._optionals)
        add._action_groups.insert(idx, req)
    add.set_defaults(func=cmd_add)


def register_remove_command(
    subparsers: _SubParsersAction,
    *,
    name: str = "remove",
    aliases: tuple[str, ...] = (),
    help_override: str | None = None,
) -> None:
    fb = "Delete a mount definition from the catalog."
    desc = parser_description_from_manual("registry remove", fb)
    if help_override:
        help_line = help_override
    else:
        help_line = help_summary_for_root("registry remove", "Remove a mount definition")
    rm = subparsers.add_parser(
        name,
        aliases=list(aliases),
        help=help_line,
        description=desc,
    )
    rm.add_argument(
        "-u",
        "--uuid",
        dest="remove_uuid",
        metavar="UUID",
        default="",
        help="Select the definition by UUID",
    )
    rm.add_argument(
        "-n",
        "--name",
        dest="remove_name",
        default="",
        help="Select the definition by name",
    )
    rm.set_defaults(func=cmd_remove)
