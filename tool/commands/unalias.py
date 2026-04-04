"""Remove persistent shell aliases/functions for WSL4AI."""

from argparse import Namespace, _SubParsersAction

from commands.alias_bash import BASH_BEGIN, BASH_END, bashrc_path
from commands.alias_ps import PS_BEGIN, PS_END, profile_paths


def _remove_marked_block(content: str, begin_marker: str, end_marker: str) -> tuple[str, bool]:
    """Remove one marked block from text content.

    Args:
        content (str): Source text where markers are searched.
        begin_marker (str): Exact begin marker line.
        end_marker (str): Exact end marker line.

    Returns:
        tuple[str, bool]:
            - Updated text content.
            - `True` if a marked block was removed, otherwise `False`.
    """
    begin_idx = content.find(begin_marker)
    end_idx = content.find(end_marker)
    if begin_idx == -1 or end_idx == -1 or end_idx <= begin_idx:
        return content, False

    end_idx += len(end_marker)
    updated = content[:begin_idx].rstrip() + "\n"
    tail = content[end_idx:].lstrip()
    if tail:
        updated += "\n" + tail
    return updated, True


def _cmd_unalias_ps(_: Namespace) -> int:
    """Remove WSL4AI function block from PowerShell profiles.

    Args:
        _ (Namespace): Parsed CLI namespace. No command-specific values are used.

    Returns:
        int: Exit code. `0` on success.
    """
    for profile in profile_paths():
        if not profile.exists():
            print(f"PowerShell profile not found: {profile}")
            continue
        existing = profile.read_text(encoding="utf-8")
        updated, removed = _remove_marked_block(existing, PS_BEGIN, PS_END)
        profile.write_text(updated, encoding="utf-8")
        state = "removed" if removed else "not found"
        print(f"PowerShell alias block {state}: {profile}")
    print("Restart terminal or run: . $PROFILE")
    return 0


def _cmd_unalias_bash(_: Namespace) -> int:
    """Remove WSL4AI function block from Bash profile.

    Args:
        _ (Namespace): Parsed CLI namespace. No command-specific values are used.

    Returns:
        int: Exit code. `0` on success.
    """
    bashrc = bashrc_path()
    if not bashrc.exists():
        print(f"Bash profile not found: {bashrc}")
        return 0
    existing = bashrc.read_text(encoding="utf-8")
    updated, removed = _remove_marked_block(existing, BASH_BEGIN, BASH_END)
    bashrc.write_text(updated, encoding="utf-8")
    state = "removed" if removed else "not found"
    print(f"Bash alias block {state}: {bashrc}")
    print("Restart shell or run: source ~/.startup-wsl4ai.sh")
    return 0


def cmd_unalias(args: Namespace) -> int:
    """Dispatch `wsl4ai unalias` to shell-specific removal logic.

    Args:
        args (Namespace): Parsed arguments with mutually exclusive flags:
            - `args.ps` (bool): Remove aliases from PowerShell profiles.
            - `args.bash` (bool): Remove alias from `~/.startup-wsl4ai.sh`.

    Returns:
        int: Exit code from selected target.
    """
    if args.ps:
        return _cmd_unalias_ps(args)
    if args.bash:
        return _cmd_unalias_bash(args)
    raise ValueError("One unalias target must be selected.")


def register_unalias_command(subparsers: _SubParsersAction) -> None:
    """Register `unalias` command and accepted target flags.

    Args:
        subparsers (_SubParsersAction): Root subparser registry.
    """
    uh = "Remove wsl4ai shortcuts from your shell"
    unalias = subparsers.add_parser("unalias", help=uh, description=uh)
    target_group = unalias.add_mutually_exclusive_group(required=True)
    target_group.add_argument("-ps", "--ps", action="store_true", help="Use PowerShell")
    target_group.add_argument("-b", "--bash", action="store_true", help="Use Bash")
    unalias.set_defaults(func=cmd_unalias)
