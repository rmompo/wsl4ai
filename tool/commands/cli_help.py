"""Help routing: if ``-h`` / ``--help`` appears, show help and ignore other options."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import textwrap

from commands.help_md import strip_subcommand_boilerplate, synthetic_blurb
from commands.style_constants import HELP_NAME, HELP_SECTION, RST

_HELP_FLAGS = frozenset(("-h", "--help"))

# Normalized section heading titles
_SECTION_ALIASES: dict[str, str] = {
    "required arguments": "Required",
    "optional arguments": "Optional",
    "options": "Optional",
    "positional arguments": "Positional",
}


def _help_styled(text: str, style: str) -> str:
    """Color ``text`` for help output when stdout is a TTY and NO_COLOR is unset."""
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return text
    return f"{style}{text}{RST}"

# Extra indent (spaces) for wrapped continuation lines (listings + argparse option help).
HELP_DESCRIPTION_CONTINUATION_EXTRA = 2


class Wsl4aiArgumentParser(argparse.ArgumentParser):
    """Parser used for the CLI tree so every subparser picks up ``Wsl4aiHelpFormatter`` by default."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", Wsl4aiHelpFormatter)
        super().__init__(*args, **kwargs)
        self._optionals.title = "Optional"

    def error(self, message: str) -> None:
        has_sub = any(isinstance(a, argparse._SubParsersAction) for a in self._actions)
        is_root = " " not in self.prog
        if is_root:
            usage_tail = "<command> [<subcommand>] [options]"
        elif has_sub:
            usage_tail = "<subcommand> [options]"
        else:
            usage_tail = "[options]"
        label = _help_styled("Usage:", HELP_SECTION)
        print(f"{label} {self.prog} [-h] {usage_tail}", file=sys.stderr)
        self.exit(2)


class Wsl4aiHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """argparse help: section headers and option names colored; continuation lines indented +2."""

    def _format_action_invocation(self, action) -> str:
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            metavar, = self._metavar_formatter(action, default)(1)
            return metavar
        short = sorted(s for s in action.option_strings if not s.startswith("--"))
        long_ = sorted(s for s in action.option_strings if s.startswith("--"))
        if action.nargs == 0:
            return ", ".join(short + long_)
        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)
        parts = list(short)
        parts.extend(f"{s} {args_string}" for s in long_)
        return ", ".join(parts)

    def start_section(self, heading: str) -> None:
        normalized = _SECTION_ALIASES.get((heading or "").lower(), (heading or "").title())
        colored = _help_styled(normalized, HELP_SECTION)
        super().start_section(colored)

    def _format_action(self, action):
        help_position = min(self._action_max_length + 2, self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2
        plain_invocation = self._format_action_invocation(action)
        colored_invocation = _help_styled(plain_invocation, HELP_NAME)
        ansi_extra = len(colored_invocation) - len(plain_invocation)
        x = HELP_DESCRIPTION_CONTINUATION_EXTRA

        if not action.help:
            action_header = "%*s%s\n" % (self._current_indent, "", colored_invocation)

        elif len(plain_invocation) <= action_width:
            action_header = "%*s%-*s  " % (
                self._current_indent, "", action_width + ansi_extra, colored_invocation
            )
            indent_first = 0

        else:
            action_header = "%*s%s\n" % (self._current_indent, "", colored_invocation)
            indent_first = help_position

        parts = [action_header]

        if action.help and action.help.strip():
            help_text = self._expand_help(action)
            if help_text:
                help_lines = self._split_lines(help_text, help_width)
                parts.append("%*s%s\n" % (indent_first, "", help_lines[0]))
                if len(help_lines) > 1:
                    rest = " ".join(help_lines[1:])
                    cont_w = max(help_width - x, 11)
                    for line in self._split_lines(rest, cont_w):
                        parts.append("%*s%s\n" % (help_position + x, "", line))

        elif not action_header.endswith("\n"):
            parts.append("\n")

        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        return self._join_parts(parts)

    def _fill_text(self, text, width, indent):
        if not text or not text.strip():
            return ""
        xs = " " * HELP_DESCRIPTION_CONTINUATION_EXTRA
        raw_lines = text.splitlines()
        if len(raw_lines) > 1:
            return "".join(
                (indent if i == 0 else indent + xs) + line + "\n"
                for i, line in enumerate(raw_lines)
            )
        collapsed = self._whitespace_matcher.sub(" ", text).strip()
        return textwrap.fill(
            collapsed,
            width,
            initial_indent=indent,
            subsequent_indent=indent + xs,
        )


# Root commands shown in general help (long names only; shorthands stay runnable but hidden).
_ROOT_LONG_COMMANDS: tuple[str, ...] = (
    "whoami",
    "registry",
    "use",
    "wsl",
    "start",
    "tui",
    "install",
)

# Commands with no nested subparsers: static action hint for general help.
_ROOT_STATIC_ACTIONS: dict[str, str] = {
    "install": "— actions: tool, database, alias.",
}


def argv_contains_help_flag(argv: list[str]) -> bool:
    """True if ``argv`` (typically ``sys.argv[1:]``) contains ``-h`` or ``--help``."""
    return any(t in _HELP_FLAGS for t in argv)


def _first_help_index(argv: list[str]) -> int | None:
    for i, t in enumerate(argv):
        if t in _HELP_FLAGS:
            return i
    return None


def _strip_option_tokens(segment: list[str]) -> list[str]:
    """Drop option flags and their values; keep positional tokens only."""
    out: list[str] = []
    i = 0
    while i < len(segment):
        t = segment[i]
        if t.startswith("-"):
            if "=" in t:
                i += 1
                continue
            i += 1
            if i < len(segment) and not segment[i].startswith("-"):
                i += 1
            continue
        out.append(t)
        i += 1
    return out


def positionals_before_help(argv: list[str]) -> list[str]:
    """Tokens before the first ``-h``/``--help``, with other options stripped."""
    idx = _first_help_index(argv)
    if idx is None:
        return []
    return _strip_option_tokens(argv[:idx])


def _get_subparsers_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction):
            return a
    return None


def _choice_help_for_primary(act: argparse._SubParsersAction, primary: str) -> str:
    """``add_parser(..., help=…)`` is stored on ``_SubParsersAction._choices_actions``, not on the subparser."""
    for pa in getattr(act, "_choices_actions", ()) or ():
        if getattr(pa, "dest", None) == primary:
            return " ".join(str(getattr(pa, "help", "") or "").split())
    return ""


def resolve_parser_for_help(
    root: argparse.ArgumentParser,
    positionals: list[str],
) -> argparse.ArgumentParser | None:
    """Walk ``positionals`` into nested subparsers. Return ``None`` if a name is unknown."""
    if not positionals:
        return root
    cur: argparse.ArgumentParser = root
    for tok in positionals:
        act = _get_subparsers_action(cur)
        if act is None:
            return None
        if tok not in act.choices:
            return None
        cur = act.choices[tok]
    return cur


def _unique_subparsers(
    act: argparse._SubParsersAction,
) -> list[tuple[str, list[str], argparse.ArgumentParser]]:
    """Return (primary_name, alias_names, parser) sorted by primary name."""
    groups: dict[int, list[str]] = {}
    for name, p in act.choices.items():
        groups.setdefault(id(p), []).append(name)
    items: list[tuple[str, list[str], argparse.ArgumentParser]] = []
    for names in groups.values():
        primary = max(names, key=len)
        aliases = sorted(n for n in names if n != primary)
        items.append((primary, aliases, act.choices[primary]))
    items.sort(key=lambda x: x[0].lower())
    return items


def _sanitize_general_desc(desc: str) -> str:
    """Strip shorthand noise from texts used in the *general* help only."""
    desc = " ".join(str(desc).split())
    desc = desc.replace("list|rl", "list")
    desc = desc.replace("add|ra", "add")
    desc = desc.replace("remove|rr", "remove")
    desc = re.sub(r"\(shortcuts[^)]*\)", "", desc, flags=re.IGNORECASE).strip()
    desc = re.sub(
        r"\s*wsl4ai\s+ws\s+is a top-level shortcut for\s+wsl4ai\s+wsl\s+set\.?\s*",
        " ",
        desc,
        flags=re.IGNORECASE,
    ).strip()
    return desc


def _terminal_columns() -> int:
    try:
        return max(40, shutil.get_terminal_size(fallback=(88, 24)).columns)
    except (OSError, AttributeError, ValueError):
        return 88


def _print_wrapped_label_desc_rows(
    rows: list[tuple[str, str]],
    *,
    line_prefix: str = "    ",
    label_pad_min: int = 0,
    gap: int = 4,
    color_labels: bool = True,
) -> None:
    """Print two columns: fixed label width, description wrapped with hanging indent."""
    if not rows:
        return
    tw = _terminal_columns()
    label_w = max(len(label) for label, _ in rows)
    if label_pad_min:
        label_w = max(label_w, label_pad_min)
    desc_width = tw - len(line_prefix) - label_w - gap
    desc_width = max(24, desc_width)
    x = HELP_DESCRIPTION_CONTINUATION_EXTRA

    for label, desc_raw in rows:
        plain_label = label
        display_label = _help_styled(label, HELP_NAME) if color_labels else label
        ansi_extra = len(display_label) - len(plain_label)
        desc = " ".join(str(desc_raw).split())
        if not desc:
            print(f"{line_prefix}{display_label}")
            continue
        lines = textwrap.wrap(
            desc,
            width=desc_width,
            break_long_words=True,
            break_on_hyphens=True,
        )
        pad = label_w + gap
        first = f"{line_prefix}{display_label:<{label_w + ansi_extra}}{' ' * gap}{lines[0]}"
        print(first)
        hang = line_prefix + (" " * (pad + x))
        if len(lines) > 1:
            cont_w = max(24, desc_width - x)
            rest = " ".join(lines[1:])
            for part in textwrap.wrap(
                rest,
                width=cont_w,
                break_long_words=True,
                break_on_hyphens=True,
            ):
                print(f"{hang}{part}")


def _actions_suffix_for_root_child(name: str, sub: argparse.ArgumentParser) -> str:
    if name in _ROOT_STATIC_ACTIONS:
        return " " + _ROOT_STATIC_ACTIONS[name]
    nested = _get_subparsers_action(sub)
    if nested is None:
        return ""
    primaries = [p for p, _, _ in _unique_subparsers(nested)]
    if not primaries:
        return ""
    return " — actions: " + ", ".join(primaries)


def print_wsl4ai_root_help(root: argparse.ArgumentParser) -> None:
    """Public entry: print the curated top-level help (no ``options:`` section)."""
    _print_root_help_long_only(root)


def print_help_for_argv(root: argparse.ArgumentParser, argv: list[str]) -> int:
    """Print help for the parser implied by positionals; unknown names fall back to root."""
    pos = positionals_before_help(argv)
    target = resolve_parser_for_help(root, pos)

    if pos == []:
        _print_root_help_long_only(root)
        return 0

    if target is None:
        print("wsl4ai: unknown command or subcommand; showing top-level help.", file=sys.stderr)
        _print_root_help_long_only(root)
        return 1

    # Router: parser has nested subcommands — custom listing with ``name (alias)``.
    if _get_subparsers_action(target) is not None:
        _print_router_help(target)
        return 0

    target.print_help()
    return 0


def _print_root_help_long_only(root: argparse.ArgumentParser) -> None:
    """Top-level ``wsl4ai -h``: usage, description, ``commands:`` only (no top-level flag list)."""
    act = _get_subparsers_action(root)
    if act is None or not hasattr(act, "choices"):
        root.print_help()
        return

    print(f"{_help_styled('Usage:', HELP_SECTION)} {root.prog} [-h] <command> [<subcommand>] [options]\n")
    if root.description:
        print(root.description + "\n")

    print(_help_styled("commands:", HELP_SECTION))
    root_rows: list[tuple[str, str]] = []
    for name in _ROOT_LONG_COMMANDS:
        sub = act.choices.get(name)
        if sub is None:
            continue
        desc = getattr(sub, "description", None) or getattr(sub, "help", None) or ""
        desc = synthetic_blurb(
            _sanitize_general_desc(desc),
            max_chars=92,
            prefer_sentence_under=100,
            fallback="",
        )
        desc = desc + _actions_suffix_for_root_child(name, sub)
        root_rows.append((name, desc))
    _print_wrapped_label_desc_rows(root_rows, label_pad_min=12)

    print(f"\n{_help_styled('Per-command help:', HELP_SECTION)} {root.prog} <command> --help")

    if root.epilog:
        print("\n" + root.epilog)


def _print_router_help(parser: argparse.ArgumentParser) -> None:
    """Help for a command with nested subparsers (e.g. ``registry``, ``use``, ``wsl``)."""
    act = _get_subparsers_action(parser)
    if act is None:
        parser.print_help()
        return

    print(f"{_help_styled('Usage:', HELP_SECTION)} {parser.prog} [-h] <subcommand> [options]\n")
    desc = getattr(parser, "description", None) or getattr(parser, "help", None) or ""
    desc = " ".join(str(desc).split())
    desc = desc.replace("list|rl", "list").replace("add|ra", "add").replace("remove|rr", "remove")
    desc = synthetic_blurb(desc, max_chars=95, prefer_sentence_under=110, fallback="")
    if desc:
        print(desc + "\n")

    print(_help_styled("subcommands:", HELP_SECTION))
    router_rows: list[tuple[str, str]] = []
    for primary, aliases, sub in _unique_subparsers(act):
        label = f"{', '.join(aliases)}, {primary}" if aliases else primary
        h = _choice_help_for_primary(act, primary)
        if not h:
            h = getattr(sub, "description", None) or getattr(sub, "help", None) or ""
            h = " ".join(str(h).split())
        h = strip_subcommand_boilerplate(h)
        h = " ".join(str(h).split())
        h = synthetic_blurb(h, max_chars=85, prefer_sentence_under=95, fallback="")
        router_rows.append((label, h))
    _print_wrapped_label_desc_rows(router_rows)

    print(f"\n{_help_styled('Per-subcommand help:', HELP_SECTION)} {parser.prog} <subcommand> --help")

    if parser.epilog:
        print("\n" + parser.epilog)
