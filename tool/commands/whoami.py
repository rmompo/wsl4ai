"""Print runtime ``machine`` and ``user`` (see ``specs/specs.md`` §1, §6)."""

from argparse import Namespace, _SubParsersAction

from commands.api import emit_from_api, api_whoami


def cmd_whoami(args: Namespace) -> int:
    """Return runtime `machine` and `user` identity as JSON envelope."""
    return emit_from_api(args, api_whoami(), [], include_data=True)


def register_whoami_command(subparsers: _SubParsersAction) -> None:
    h = "Print the machine and user identities for this session"
    sub = subparsers.add_parser(
        "whoami",
        help=h,
        description=h,
    )
    sub.set_defaults(func=cmd_whoami)

    wai = subparsers.add_parser("wai", help="Shorthand for whoami", description="Shorthand for whoami")
    wai.set_defaults(func=cmd_whoami)
