"""`wsl4ai install tool`: ensure required app layout exists."""

from argparse import Namespace
from commands.common import APP_DIR, DDBB_DIR, MAN_DIR
from commands.api_json import emit_envelope


def cmd_install_tool(args: Namespace) -> int:
    """Create tool directories if missing and report the app root."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    DDBB_DIR.mkdir(parents=True, exist_ok=True)
    MAN_DIR.mkdir(parents=True, exist_ok=True)
    return emit_envelope(
        args=args,
        command="install",
        subcommand="tool",
        status=0,
        message=f"tool layout verified: {APP_DIR}",
    )
