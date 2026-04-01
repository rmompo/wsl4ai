"""Bash alias installation helpers for WSL4AI."""

from argparse import Namespace
from pathlib import Path
import sys

BASH_BEGIN = "# >>> WSL4AI BEGIN >>>"
BASH_END = "# <<< WSL4AI END <<<"


def bashrc_path() -> Path:
    """Return the default Bash profile path for the current user.

    Returns:
        Path: `~/.bashrc`.
    """
    return Path.home() / ".bashrc"


def wsl4ai_block() -> str:
    """Build the WSL4AI shell function block for Bash.

    Returns:
        str: Text block bounded by WSL4AI markers. The function forwards all
            positional arguments (`"$@"`) to `wsl4ai.py` via the current Python
            interpreter.
    """
    script_path = str((Path(__file__).resolve().parent.parent / "wsl4ai.py"))
    python_exe = sys.executable
    return (
        f"{BASH_BEGIN}\n"
        f"wsl4ai() {{\n"
        f"  \"{python_exe}\" \"{script_path}\" \"$@\"\n"
        f"}}\n"
        f"{BASH_END}\n"
    )


def upsert_block(content: str, block: str) -> tuple[str, bool]:
    """Insert or replace the WSL4AI block in Bash profile content.

    Args:
        content (str): Existing `~/.bashrc` contents.
        block (str): WSL4AI block that includes begin/end markers.

    Returns:
        tuple[str, bool]:
            - Updated profile content.
            - `True` if inserted, `False` if replaced.
    """
    begin_idx = content.find(BASH_BEGIN)
    end_idx = content.find(BASH_END)

    if begin_idx != -1 and end_idx != -1 and end_idx > begin_idx:
        end_idx += len(BASH_END)
        updated = (content[:begin_idx].rstrip() + "\n\n" + block + content[end_idx:].lstrip())
        return updated, False

    suffix = "" if content.endswith(("\n", "\r")) or not content else "\n\n"
    return content + suffix + block, True


def cmd_alias_bash(_: Namespace) -> int:
    """Install or overwrite the WSL4AI Bash function alias.

    Args:
        _ (Namespace): Parsed CLI namespace. No command-specific values are
            consumed.

    Returns:
        int: Exit code. `0` on success.
    """
    bashrc = bashrc_path()
    bashrc.parent.mkdir(parents=True, exist_ok=True)
    existing = bashrc.read_text(encoding="utf-8") if bashrc.exists() else ""
    updated, created = upsert_block(existing, wsl4ai_block())
    bashrc.write_text(updated, encoding="utf-8")
    state = "installed" if created else "updated"
    print(f"Bash profile {state}: {bashrc}")
    print("Restart shell or run: source ~/.bashrc")
    return 0
