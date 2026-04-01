"""Print runtime ``machine`` and ``user`` (see ``specs/specs.md`` §1, §6)."""

from argparse import Namespace, _SubParsersAction

from commands.api_json import emit_envelope, row_from_pairs


def cmd_whoami(args: Namespace) -> int:
    """Return runtime `machine` and `user` identity as JSON envelope."""
    rows = [row_from_pairs([("machine", args.machine), ("user", args.user)])]
    return emit_envelope(
        args=args,
        command="whoami",
        subcommand="",
        status=0,
        message="runtime identity",
        rows=rows,
        include_data=True,
    )


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
