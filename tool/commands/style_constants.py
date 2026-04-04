"""Semantic ANSI styles for WSL4AI terminal output (SGR 41/42 backgrounds, 97 bright white text)."""

import os
import sys

RST = "\x1b[0m"

# Bright white foreground (``97``), then background — order helps some Windows consoles
# that mis-render ``42;97`` (green + bright white) as black text.
_BG_RED = "41"
_BG_GREEN = "42"
_FG_WHITE_BRIGHT = "97"

# Registry row title in ``list`` when linked (busy).
LIST_IN_USE = f"\x1b[{_FG_WHITE_BRIGHT};{_BG_RED}m"

# Registry row title in ``list`` when not linked (free).
LIST_NOT_IN_USE = f"\x1b[{_FG_WHITE_BRIGHT};{_BG_GREEN}m"

# Success-style messages (e.g. ``add`` confirmation).
GENERAL_OK = f"\x1b[{_FG_WHITE_BRIGHT};{_BG_GREEN}m"

# Error-style messages (e.g. ``add`` failures).
GENERAL_ERROR = f"\x1b[{_FG_WHITE_BRIGHT};{_BG_RED}m"


def tty_styled(text: str, style: str, *, stream=None) -> str:
    """Wrap ``text`` with ``style`` + RST when ``stream`` is a TTY and NO_COLOR is unset."""
    out = sys.stdout if stream is None else stream
    if os.environ.get("NO_COLOR") or not out.isatty():
        return text
    return f"{style}{text}{RST}"


# Help formatting colors
HELP_SECTION = "\x1b[1;33m"   # bold yellow — Required / Optional / commands / subcommands
HELP_NAME = "\x1b[1;36m"      # bold cyan   — command / subcommand / option names
