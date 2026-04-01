"""Alias command router for shell-specific targets."""

from argparse import Namespace, _SubParsersAction

from commands.alias_bash import cmd_alias_bash
from commands.alias_ps import cmd_alias_ps


def cmd_alias(args: Namespace) -> int:
    """Dispatch `wsl4ai alias` to the requested shell implementation.

    Args:
        args (Namespace): Parsed arguments with mutually exclusive flags:
            - `args.ps` (bool): Install aliases for PowerShell profiles.
            - `args.bash` (bool): Install aliases for Bash profile.

    Returns:
        int: Command exit code from selected shell handler.

    Raises:
        ValueError: If no target flag is selected.
    """
    if args.ps:
        return cmd_alias_ps(args)
    if args.bash:
        return cmd_alias_bash(args)
    raise ValueError("One alias target must be selected.")


def register_alias_command(subparsers: _SubParsersAction) -> None:
    """Register `alias` command and accepted target flags.

    Args:
        subparsers (_SubParsersAction): Root subparser registry where the
            command will be attached.
    """
    ah = "Add wsl4ai shortcuts to your shell"
    alias = subparsers.add_parser("alias", help=ah, description=ah)
    target_group = alias.add_mutually_exclusive_group(required=True)
    target_group.add_argument("-ps", "--ps", action="store_true", help="Use PowerShell")
    target_group.add_argument("-b", "--bash", action="store_true", help="Use Bash")
    alias.set_defaults(func=cmd_alias)
