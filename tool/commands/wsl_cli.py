"""Router ``wsl4ai wsl`` and root shortcut ``ws`` (``wsl set``)."""

from argparse import Namespace, _SubParsersAction

from commands.api_json import OptionSpec, emit_envelope, options_from_args, row_from_pairs
from commands.common import DB_PATH, connect_db, require_database_file
from commands.help_md import help_summary_for_root, parser_description_from_manual
from commands.wsl_db import resolve_wsl_uuid


def cmd_wsl_set(args: Namespace) -> int:
    opts = options_from_args(
        args,
        [
            OptionSpec("--cli", "wsl_cli"),
            OptionSpec("--wsl-uuid", "wsl_set_wsl_uuid"),
            OptionSpec("--wsl-name", "wsl_set_wsl_name"),
        ],
    )
    if not require_database_file():
        return emit_envelope(args=args, command="wsl", subcommand="set", options=opts, status=1, message="database file not found")
    cli_val = (getattr(args, "wsl_cli", None) or "").strip()
    if not cli_val:
        return emit_envelope(args=args, command="wsl", subcommand="set", options=opts, status=1, message="wsl set: --cli must be non-empty")
    ri = args.runtime_identity
    with connect_db(DB_PATH) as con:
        wsl_id, err = resolve_wsl_uuid(
            con,
            wsl_uuid=getattr(args, "wsl_set_wsl_uuid", "") or "",
            wsl_name=getattr(args, "wsl_set_wsl_name", "") or "",
            runtime_user=ri.user,
            runtime_wsl_name=ri.wsl_name,
            create_if_missing=False,
            msg_prefix="wsl set",
        )
        if err:
            return emit_envelope(args=args, command="wsl", subcommand="set", options=opts, status=1, message=err)
        con.execute(
            "UPDATE wsls SET cli_command = ? WHERE uuid = ?",
            (cli_val, wsl_id),
        )
    return emit_envelope(
        args=args,
        command="wsl",
        subcommand="set",
        options=opts,
        status=0,
        message="wsl set: cli_command updated",
        rows=[row_from_pairs([("wslUuid", wsl_id), ("cliCommand", cli_val)])],
    )


def cmd_wsl_list(args: Namespace) -> int:
    """List all known WSL rows and their launch commands."""
    opts: list[dict[str, str]] = []
    if not require_database_file():
        return emit_envelope(args=args, command="wsl", subcommand="list", options=opts, status=1, message="database file not found")
    with connect_db(DB_PATH) as con:
        rows = con.execute(
            """
            SELECT uuid, name, user, cli_command
            FROM wsls
            ORDER BY name COLLATE NOCASE, user COLLATE NOCASE
            """
        ).fetchall()
        if not rows:
            return emit_envelope(args=args, command="wsl", subcommand="list", options=opts, status=0, message="no WSL rows found", rows=[])
        out_rows: list[dict[str, list[dict[str, str]]]] = []
        for uid, name, user, cli in rows:
            cli_str = (cli or "").strip()
            out_rows.append(
                row_from_pairs(
                    [
                        ("wslUuid", uid),
                        ("wslName", name),
                        ("wslUser", user),
                        ("cliCommand", cli_str if cli_str else "<unset>"),
                    ]
                )
            )
    return emit_envelope(
        args=args,
        command="wsl",
        subcommand="list",
        options=opts,
        status=0,
        message=f"listed {len(out_rows)} WSL row(s)",
        rows=out_rows,
    )


def _add_wsl_set_args(p) -> None:
    p.add_argument(
        "-c",
        "--cli",
        dest="wsl_cli",
        required=True,
        metavar="VALUE",
        help="Command this WSL workspace should run when invoked",
    )
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument(
        "-wu",
        "--wsl-uuid",
        dest="wsl_set_wsl_uuid",
        default="",
        metavar="UUID",
        help="WSL UUID (optional; omit to target runtime WSL)",
    )
    g.add_argument(
        "-wn",
        "--wsl-name",
        dest="wsl_set_wsl_name",
        default="",
        help="WSL name (optional; omit to target runtime WSL)",
    )


def register_wsl_set_parser(
    subparsers: _SubParsersAction,
    *,
    name: str,
    aliases: tuple[str, ...] = (),
    help_override: str | None = None,
) -> None:
    fb = "Set which command runs when this WSL workspace is started."
    desc = parser_description_from_manual("wsl / ws", fb)
    if help_override:
        help_line = help_override
    else:
        help_line = help_summary_for_root("wsl / ws", "Set a WSL launch command")
    p = subparsers.add_parser(
        name,
        aliases=list(aliases),
        help=help_line,
        description=desc,
    )
    _add_wsl_set_args(p)
    p.set_defaults(func=cmd_wsl_set)


def register_wsl_command(subparsers: _SubParsersAction) -> None:
    """Register ``wsl`` with nested ``set`` (and alias ``ws`` on nested subparser if desired)."""
    wsl_fb = "Adjust per-WSL launch command using the set subcommand."
    wsl_desc = parser_description_from_manual("wsl / ws", wsl_fb)
    help_line = help_summary_for_root("wsl / ws", "Configure WSL launch commands")
    wsl = subparsers.add_parser(
        "wsl",
        help=help_line,
        description=wsl_desc,
    )
    wsl_sub = wsl.add_subparsers(
        dest="wsl_command",
        required=True,
        metavar="SUBCOMMAND",
        help="list | set",
    )
    list_help = "Show all WSL workspaces tracked by wsl4ai"
    lst = wsl_sub.add_parser("list", aliases=["wl"], help=list_help, description=list_help)
    lst.set_defaults(func=cmd_wsl_list)

    register_wsl_set_parser(wsl_sub, name="set")


def register_wsl_root_shortcuts(subparsers: _SubParsersAction) -> None:
    """Top-level shortcuts: `wl` and `ws`."""
    wl = subparsers.add_parser("wl", help="Shorthand for wsl list")
    wl.set_defaults(func=cmd_wsl_list)

    register_wsl_set_parser(
        subparsers,
        name="ws",
        help_override="Shorthand for wsl set",
    )
