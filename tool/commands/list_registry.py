"""List all registry rows."""

import os
from argparse import Namespace, _SubParsersAction
from pathlib import Path

from commands.api_json import emit_envelope, row_from_pairs
from commands.common import DB_PATH, connect_db, expand_path_template, load_local_env_paths, require_database_file
from commands.help_md import help_summary_for_root, parser_description_from_manual


def _resolved_path_line(base_raw: str, rel_segment: str) -> str:
    """Same expansion/join as ``add`` (see ``expand_path_template``, ``join``, ``normpath``)."""
    root = expand_path_template(base_raw or "")
    rel = (rel_segment or "").strip()
    return str(Path(os.path.normpath(os.path.join(root, rel))))


def cmd_list(_: Namespace) -> int:
    """Return all `registries` rows with resolved paths and linked `uses`."""
    if not require_database_file():
        return emit_envelope(
            args=_,
            command="registry",
            subcommand="list",
            status=1,
            message="database file not found",
        )
    with connect_db(DB_PATH) as con:
        param_host, param_local = load_local_env_paths()
        rows = con.execute(
            """
            SELECT uuid, name, rel_path_host, rel_path_wsl
            FROM registries
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()
        out_rows: list[dict[str, list[dict[str, str]]]] = []
        if not rows:
            return emit_envelope(
                args=_,
                command="registry",
                subcommand="list",
                status=0,
                message="no registry entries",
                rows=[],
            )
        for reg_uuid, name, host_rel, wsl_rel in rows:
            in_use = con.execute(
                """
                SELECT w.uuid, w.name, w.user, s.mounted
                FROM uses s
                JOIN wsls w ON w.uuid = s.wsl_uuid
                WHERE s.registry_uuid = ?
                ORDER BY w.name COLLATE NOCASE, w.user COLLATE NOCASE
                """,
                (reg_uuid,),
            ).fetchall()
            host_path = _resolved_path_line(param_host, host_rel)
            wsl_path = _resolved_path_line(param_local, wsl_rel)
            out_rows.append(
                row_from_pairs(
                    [
                        ("registryUuid", reg_uuid),
                        ("registryName", name),
                        ("hostPath", host_path),
                        ("wslPath", wsl_path),
                        ("inUse", "true" if in_use else "false"),
                    ]
                )
            )
            for w_uuid, w_name, w_user, mounted in in_use:
                out_rows.append(
                    row_from_pairs(
                        [
                            ("registryUuid", reg_uuid),
                            ("registryName", name),
                            ("wslUuid", w_uuid),
                            ("wslName", w_name),
                            ("wslUser", w_user),
                            ("mounted", str(int(mounted))),
                        ]
                    )
                )
    return emit_envelope(
        args=_,
        command="registry",
        subcommand="list",
        status=0,
        message=f"listed {len(out_rows)} row(s)",
        rows=out_rows,
    )


def register_list_command(
    subparsers: _SubParsersAction,
    *,
    name: str = "list",
    aliases: tuple[str, ...] = (),
    help_override: str | None = None,
) -> None:
    """Register ``list`` subparser (e.g. under ``registry`` or as root shortcut ``rl``)."""
    fb = "Show every mount definition and which WSL workspaces reference it."
    desc = parser_description_from_manual("registry list", fb)
    if help_override:
        help_line = help_override
    else:
        help_line = help_summary_for_root("registry list", "List mount definitions")
    lst = subparsers.add_parser(
        name,
        aliases=list(aliases),
        help=help_line,
        description=desc,
    )
    lst.set_defaults(func=cmd_list)
