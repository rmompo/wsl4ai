"""Print how this WSL distro is set up (see ``specs/tool/specs-info.md``)."""

from argparse import Namespace, _SubParsersAction

from commands.api import emit_from_api, api_info


def cmd_info(args: Namespace) -> int:
    """Return the read-only setup report as a JSON envelope."""
    return emit_from_api(args, api_info(), [], include_data=True)


def register_info_command(subparsers: _SubParsersAction) -> None:
    h = "Show how this WSL distro is set up (identity, paths, mounts, database, config, AI client)"
    sub = subparsers.add_parser("info", help=h, description=h)
    sub.set_defaults(func=cmd_info)

    inf = subparsers.add_parser("inf", help="Shorthand for info", description="Shorthand for info")
    inf.set_defaults(func=cmd_info)
