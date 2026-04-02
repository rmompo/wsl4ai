"""`wsl4ai start`: run a mounted use in foreground."""

from __future__ import annotations

import os
import subprocess
from argparse import Namespace, _SubParsersAction

from commands.api_json import OptionSpec, emit_envelope, options_from_args
from commands.common import DB_PATH, connect_db, expand_path_template, load_local_env_paths, require_database_file
from commands.help_md import help_summary_for_root, parser_description_from_manual
from commands.wsl_db import resolve_registry_target, resolve_wsl_uuid


def cmd_start(args: Namespace) -> int:
    """Run `wsls.cli_command` for one concrete use in the current console."""
    opts = options_from_args(
        args,
        [
            OptionSpec("--registry-uuid", "start_registry_uuid"),
            OptionSpec("--registry-name", "start_registry_name"),
            OptionSpec("--wsl-uuid", "start_wsl_uuid"),
            OptionSpec("--wsl-name", "start_wsl_name"),
        ],
    )
    if not require_database_file():
        return emit_envelope(args=args, command="start", options=opts, status=1, message="database file not found")

    ri = args.runtime_identity
    with connect_db(DB_PATH) as con:
        reg_id, reg_err = resolve_registry_target(
            con,
            registry_uuid=getattr(args, "start_registry_uuid", "") or "",
            registry_name=getattr(args, "start_registry_name", "") or "",
            prefix="start",
        )
        if reg_err:
            return emit_envelope(args=args, command="start", options=opts, status=1, message=reg_err)

        wsl_id, wsl_err = resolve_wsl_uuid(
            con,
            wsl_uuid=getattr(args, "start_wsl_uuid", "") or "",
            wsl_name=getattr(args, "start_wsl_name", "") or "",
            runtime_user=ri.user,
            runtime_wsl_name=ri.wsl_name,
            create_if_missing=False,
            msg_prefix="start",
        )
        if wsl_err:
            return emit_envelope(args=args, command="start", options=opts, status=1, message=wsl_err)

        row = con.execute(
            """
            SELECT s.mounted, r.rel_path_wsl, w.cli_command
            FROM uses s
            JOIN registries r ON r.uuid = s.registry_uuid
            JOIN wsls w ON w.uuid = s.wsl_uuid
            WHERE s.registry_uuid = ? AND s.wsl_uuid = ?
            """,
            (reg_id, wsl_id),
        ).fetchone()
        if not row:
            return emit_envelope(args=args, command="start", options=opts, status=1, message="start: use link not found")

        mounted, rel_path_wsl, cli_command = row
        if int(mounted) != 1:
            return emit_envelope(
                args=args,
                command="start",
                options=opts,
                status=1,
                message="start: blocked by safety rule (use must be mounted=1)",
            )

    _, base_path_wsl = load_local_env_paths()

    cli = str(cli_command or "").strip()
    if not cli:
        return emit_envelope(args=args, command="start", options=opts, status=1, message="start: empty wsls.cli_command")

    root = expand_path_template(str(base_path_wsl or ""))
    if not root:
        return emit_envelope(args=args, command="start", options=opts, status=1, message="start: missing WSL_PROJECTS in local.env")

    workdir = os.path.normpath(os.path.join(root, str(rel_path_wsl or "").strip()))
    if not os.path.isdir(workdir):
        return emit_envelope(args=args, command="start", options=opts, status=1, message=f"start: target directory not found: {workdir}")

    try:
        proc = subprocess.run(cli, shell=True, cwd=workdir, check=False)
    except Exception as exc:
        return emit_envelope(args=args, command="start", options=opts, status=1, message=f"start: execution failed: {exc}")

    if int(proc.returncode) != 0:
        return emit_envelope(
            args=args,
            command="start",
            options=opts,
            status=int(proc.returncode),
            message=f"start: command exited with status {int(proc.returncode)}",
        )
    return emit_envelope(args=args, command="start", options=opts, status=0, message="start: command finished successfully")


def register_start_command(subparsers: _SubParsersAction) -> None:
    """Register the concrete `start` command."""
    fb = "Run one mounted use: cd to WSL path and execute this WSL cli command."
    desc = parser_description_from_manual("start", fb)
    help_line = help_summary_for_root("start", "Run one mounted use in the current console")
    p = subparsers.add_parser("start", help=help_line, description=desc)
    reg = p.add_mutually_exclusive_group(required=True)
    reg.add_argument(
        "-ru",
        "--registry-uuid",
        dest="start_registry_uuid",
        default="",
        metavar="UUID",
        help="Registry UUID for the target use",
    )
    reg.add_argument(
        "-rn",
        "--registry-name",
        dest="start_registry_name",
        default="",
        help="Registry name for the target use",
    )
    wsl = p.add_mutually_exclusive_group(required=False)
    wsl.add_argument(
        "-wu",
        "--wsl-uuid",
        dest="start_wsl_uuid",
        default="",
        metavar="UUID",
        help="WSL UUID (optional; omit to use runtime WSL)",
    )
    wsl.add_argument(
        "-wn",
        "--wsl-name",
        dest="start_wsl_name",
        default="",
        help="WSL name (optional; omit to use runtime WSL)",
    )
    p.set_defaults(func=cmd_start)
