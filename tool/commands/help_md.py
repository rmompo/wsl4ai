"""Extract short argparse help strings from ``man/wsl4ia-man.md``.

Goal: keep the regular argparse ``--help/-h`` format, but reuse the
authoritative command descriptions from the markdown manual.
"""

from __future__ import annotations

import re
from functools import lru_cache

from commands.common import MAN_DIR


_MANUAL_MD_PATH = MAN_DIR / "wsl4ia-man.md"

_HEADING_BY_KEY: dict[str, str] = {
    # Core commands
    "whoami": "### 1.a `whoami`",
    "registry list": "### 1.b `registry list`",
    "registry add": "### 1.c `registry add`",
    "registry remove": "### 1.d `registry remove`",
    "use": "### 1.e `use`",
    "wsl / ws": "### 1.f `wsl` / `ws`",
    "start": "### 1.g `start`",
    "tui": "### 1.h `tui`",
    # Special commands
    "alias": "### 2.a `alias`",
    "unalias": "### 2.b `unalias`",
    "install": "### 2.c `install`",
}


def _clean_md_for_argparse(text: str) -> str:
    """Remove a few markdown markers so argparse output is readable."""
    # Inline code backticks -> plain text
    text = text.replace("`", "")
    # Bold markers
    text = text.replace("**", "")
    # Collapse whitespace/newlines
    return " ".join(text.split())


def strip_subcommand_boilerplate(text: str) -> str:
    """Drop a leading ``Subcommand of <name>.`` from manual-derived paragraphs.

    Registry (and similar) sections start with that phrase; summaries should use
    the following sentence so router listings stay meaningful.
    """
    text = " ".join(str(text).split())
    if not text:
        return text
    return re.sub(r"^Subcommand of\s+[^.]+\.\s*", "", text, count=1, flags=re.IGNORECASE)


def synthetic_blurb(
    text: str,
    *,
    max_chars: int = 88,
    prefer_sentence_under: int = 96,
    fallback: str = "",
) -> str:
    """Short synthetic line: first sentence if reasonably short, else truncate."""
    raw = " ".join(str(text).split())
    raw = strip_subcommand_boilerplate(raw)
    raw = " ".join(raw.split())
    if not raw:
        return fallback
    for sep in (". ", "? ", "! "):
        p = raw.find(sep)
        if 0 < p < prefer_sentence_under:
            return raw[: p + 1].strip()
    if len(raw) <= max_chars:
        return raw
    return raw[: max(1, max_chars - 3)].rstrip() + "..."


def parser_description_from_manual(key: str, fallback: str = "") -> str:
    """Short ``description=`` text: prefer curated ``fallback`` (user goal), not manual logic."""
    if fallback.strip():
        return synthetic_blurb(fallback.strip(), max_chars=98, prefer_sentence_under=110, fallback=fallback.strip())
    para = help_from_manual(key, "")
    return synthetic_blurb(para, max_chars=98, prefer_sentence_under=110, fallback="")


@lru_cache(maxsize=1)
def _read_manual_lines() -> list[str]:
    try:
        raw = _MANUAL_MD_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return raw.splitlines()


def help_summary_for_root(key: str, fallback: str = "") -> str:
    """Short ``help=`` line: prefer ``fallback`` (goal); else first paragraph from the manual."""
    if fallback.strip():
        return synthetic_blurb(fallback.strip(), max_chars=70, prefer_sentence_under=78, fallback=fallback.strip())
    long = help_from_manual(key, "")
    if not long:
        return ""
    return synthetic_blurb(long.strip(), max_chars=70, prefer_sentence_under=78, fallback="")


@lru_cache(maxsize=None)
def help_from_manual(key: str, fallback: str = "") -> str:
    """Get the first paragraph after a known manual heading."""
    heading = _HEADING_BY_KEY.get(key)
    if not heading:
        return fallback

    lines = _read_manual_lines()
    if not lines:
        return fallback

    heading_idx = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            heading_idx = i
            break
    if heading_idx is None:
        return fallback

    # Start after heading; skip empty lines
    i = heading_idx + 1
    while i < len(lines) and not lines[i].strip():
        i += 1

    if i >= len(lines):
        return fallback

    # Collect the first paragraph: until blank line or code block or next heading.
    paragraph_lines: list[str] = []
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            break
        if s.startswith("```"):
            break
        if s.startswith("###"):
            break
        if s.startswith("---"):
            break
        paragraph_lines.append(lines[i])
        i += 1

    if not paragraph_lines:
        return fallback

    return _clean_md_for_argparse(" ".join(paragraph_lines))


def root_description_short() -> str:
    """One-line summary for top-level ``wsl4ai -h`` (list of commands)."""
    return "WSL4AI — mount definitions, WSL machines, and attaching them."


def root_epilog_short() -> str:
    """Short footer after the command list on ``wsl4ai -h``."""
    return ""

