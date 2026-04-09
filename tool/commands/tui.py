"""Textual-based Text User Interface for WSL4AI."""
from __future__ import annotations

import json
import logging
from argparse import Namespace
from pathlib import Path

_LOG_CONF    = Path(__file__).resolve().parent.parent / "conf" / "config.json"
_TOOL_DIR    = Path(__file__).resolve().parent.parent   # tool/  (where wsl4ai.py lives)
_LOG_DEFAULT = "wsl4ai.log"


def _resolve_log_path(file_val: str) -> Path:
    """Resolve log.file value to an absolute Path.

    Relative paths and "." are resolved relative to the tool/ directory
    (the folder that contains wsl4ai.py).

    Examples (tool/ = /path/to/wsl4ai/tool):
      "wsl4ai.log"      → tool/wsl4ai.log
      "logs/wsl4ai.log" → tool/logs/wsl4ai.log
      "."               → tool/wsl4ai.log
      "/var/log/x.log"  → /var/log/x.log   (absolute, used as-is)

    ``~``, ``$HOME``, and ``${HOME}`` are expanded in all cases.
    """
    import os
    s = file_val.strip()
    s = os.path.expanduser(s)
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or ""
    if home:
        s = s.replace("${HOME}", home).replace("$HOME", home)
    s = os.path.expandvars(s)

    if s == ".":
        return _TOOL_DIR / _LOG_DEFAULT

    p = Path(s)
    if not p.is_absolute():
        p = _TOOL_DIR / p
    return p


def _configure_logging() -> None:
    """Read log.level and log.file from config.json and configure the root logger.

    Supported levels: DEBUG, INFO, WARNING, ERROR, NONE (disables all logging).
    Defaults to WARNING when the key is absent or unrecognised.
    log.file defaults to '.' (same folder as config.json).
    The log directory is created automatically if it does not exist.
    """
    level_name = "WARNING"
    file_val   = "."
    try:
        cfg        = json.loads(_LOG_CONF.read_text(encoding="utf-8"))
        log_cfg    = cfg.get("log", {})
        level_name = str(log_cfg.get("level", "WARNING")).strip().upper()
        file_val   = str(log_cfg.get("file",  ".")).strip() or "."
    except Exception:
        pass

    if level_name == "NONE":
        logging.disable(logging.CRITICAL)
        return

    log_path = _resolve_log_path(file_val)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # fall through; basicConfig will fail gracefully if dir is unwritable

    numeric = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(
        filename=log_path, level=numeric,
        format="%(asctime)s %(levelname)s %(message)s",
        filemode="a",
    )

try:
    from textual.app import App, ComposeResult
    from textual.widget import Widget
    from textual import events
    from rich.text import Text
    _HAS_TEXTUAL = True
except ImportError:
    _HAS_TEXTUAL = False


# ─── Banner ───────────────────────────────────────────────────────────────────

_APP_VERSION: str = ""          # set by cmd_tui before launching the app
_BANNER_MAGENTA = "#ff00ff"     # fixed bright magenta for octopus body

BANNER_BODY = [
    "▄███▄",
    "█▀◉◉▀█",
    "▀█▄▄█▀",
    "▄▀▄▄▄▀",
]
BANNER_TENTACLES = [
    "",
    "",
    "▃▄▂▂▁",
    "▄▃▄▂▃▂▂▁",
]
BANNER_GITHUB = "https://github.com/rmompo/wsl4ai"

# ─── Theme ────────────────────────────────────────────────────────────────────

_TOOL_DIR    = Path(__file__).resolve().parent.parent   # tool/
_THEMES_DIR  = _TOOL_DIR / "tui_themes"
_THEME_CFG   = _TOOL_DIR.parent / "conf" / "config.json"
_DEFAULT_THEME = "normal_dark"

# Active styles — populated by _load_theme()
# item_sel is always auto-computed as the inverse of item (not stored in theme files).
# button_sel can be overridden per-theme; defaults to the inverse of button.
_S: dict[str, str] = {
    "lines":      "dim",
    "item":       "",
    "item_sel":   "bold reverse",
    "label":      "bold",
    "button":     "bold",
    "button_sel": "bold reverse",
    "text":       "",
    "text_hl":    "bold",
    "text_ok":    "green bold",
    "text_err":   "red bold",
    "input":      "",
    "input_sel":  "bold reverse",
}
_THEME_DARK: bool = True  # set by _load_theme(); drives Textual dark/light mode


def _load_theme() -> None:
    """Read config.json and load the configured theme into _S (in-place)."""
    global _THEME_DARK
    theme_id = _DEFAULT_THEME
    try:
        cfg = json.loads(_THEME_CFG.read_text(encoding="utf-8"))
        theme_id = str(cfg.get("tui", {}).get("theme", _DEFAULT_THEME)).strip() or _DEFAULT_THEME
    except Exception:
        pass
    raw: dict = {}
    data: dict = {}
    try:
        data = json.loads((_THEMES_DIR / f"{theme_id}.json").read_text(encoding="utf-8"))
        raw = data.get("styles", {}) if isinstance(data, dict) else {}
    except Exception:
        pass
    # "dark" key is at top level of the theme JSON (not inside "styles")
    if "dark" in data:
        _THEME_DARK = bool(data["dark"])
    else:
        _THEME_DARK = "light" not in theme_id.lower()
    logging.debug("_load_theme: theme_id=%s  dark_key_in_file=%r  _THEME_DARK=%s", theme_id, data.get("dark", "MISSING"), _THEME_DARK)
    logging.debug("_load_theme: item=%r  lines=%r", raw.get("item"), raw.get("lines"))
    _S["lines"]  = raw.get("lines",  "dim")
    _S["item"]   = raw.get("item",   "")
    _S["label"]  = raw.get("label",  "bold")
    _S["button"] = raw.get("button", "bold")
    _S["text"]     = raw.get("text",     "")
    _S["text_hl"]  = raw.get("text_hl",  "bold")
    _S["text_ok"]  = raw.get("text_ok",  "green bold")
    _S["text_err"] = raw.get("text_err", "red bold")
    _S["input"]    = raw.get("input",    "")
    # input_sel: explicit theme override or auto-invert from input
    if "input_sel" in raw:
        _S["input_sel"] = raw["input_sel"]
    else:
        inp = _S["input"]
        _S["input_sel"] = (inp + " reverse").strip() if inp else "bold reverse"
    # item_sel: always the inverse of item (UX spec — not stored in theme)
    item = _S["item"]
    _S["item_sel"] = (item + " reverse").strip() if item else "bold reverse"
    # button_sel: explicit theme override or auto-invert from button
    if "button_sel" in raw:
        _S["button_sel"] = raw["button_sel"]
    else:
        btn = _S["button"]
        _S["button_sel"] = (btn + " reverse").strip() if btn else "bold reverse"


# ─── Theme map ────────────────────────────────────────────────────────────────
# Maps (submenu_label, ...) path segments after "Theme" → theme file id

_THEME_MAP: dict[tuple, str] = {
    ("Dark",  "Normal"):      "normal_dark",
    ("Dark",  "Bright"):      "bright_dark",
    ("Dark",  "Color Blind"): "color_blind_dark",
    ("Light", "Normal"):      "normal_light",
    ("Light", "Bright"):      "bright_light",
    ("Light", "Color Blind"): "color_blind_light",
    ("High Contrast",):       "high_contrast",
}

# Ordered list of (display_name, theme_id) for ThemeDialog
_THEME_LIST: list[tuple[str, str]] = [
    ("Dark  › Normal",      "normal_dark"),
    ("Dark  › Bright",      "bright_dark"),
    ("Dark  › Color Blind", "color_blind_dark"),
    ("Light › Normal",      "normal_light"),
    ("Light › Bright",      "bright_light"),
    ("Light › Color Blind", "color_blind_light"),
    ("High Contrast",       "high_contrast"),
]


def _current_theme_id() -> str:
    """Read the active theme_id from config.json, falling back to default."""
    try:
        cfg = json.loads(_THEME_CFG.read_text(encoding="utf-8"))
        return str(cfg.get("tui", {}).get("theme", _DEFAULT_THEME)).strip() or _DEFAULT_THEME
    except Exception:
        return _DEFAULT_THEME


def _save_theme(theme_id: str) -> None:
    """Persist theme_id to conf/config.json under tui.theme."""
    try:
        try:
            cfg = json.loads(_THEME_CFG.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
        cfg.setdefault("tui", {})["theme"] = theme_id
        _THEME_CFG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logging.warning("_save_theme: could not write config: %s", exc)


def _notify_err(app_or_widget, msg: str, timeout: int = 4) -> None:
    """Log an error and show it as a Textual notification."""
    logging.error(msg)
    app_or_widget.notify(msg, timeout=timeout)


# ─── Menu definition ──────────────────────────────────────────────────────────
# str         → leaf action (direct dispatch on enter)
# (str, list) → item with submenu children
# None        → visual separator (only valid inside submenu lists)

MENU: list = [
    ("Registry", ["List", None, "Add", "Remove"]),
    ("Use", ["List", None, "Add", "Remove", None, "Enable", "Disable"]),
    ("Wsl", ["List", None, "Set"]),
    "Start",
    ("Others", [
        ("Install", [
            "Database",
            ("Alias", ["List", None, "Add", "Remove"]),
        ]),
        None,
        "Theme",
    ]),
    "Exit",
]

_OTHERS_IDX = 4  # index of "Others" in MENU — rendered with │…│ box in bar


# ─── Menu helpers ─────────────────────────────────────────────────────────────

def _label(item) -> str:
    """Display label for any menu entry."""
    if item is None:
        return ""
    return item[0] if isinstance(item, tuple) else item


def _kids(item) -> list | None:
    """Submenu list for an item, or None if leaf."""
    return item[1] if isinstance(item, tuple) else None


def _dropdown_iw(items: list) -> int:
    """Inner width for a dropdown: widest content cell, min 6."""
    w = 0
    for it in items:
        if it is None:
            continue
        s = _label(it)
        if _kids(it) is not None:
            s += " »"
        w = max(w, len(s))
    return max(w, 6)


# ─── Bar layout ───────────────────────────────────────────────────────────────

def _bar_layout() -> list[tuple[int, int]]:
    """Return (label_x, label_w) for each top-level MENU item.

    Layout rules:
    - 2-cell left margin (1 border space + 1 separation space outside highlight).
    - Normal items: label + 1-cell gap.
    - Others (boxed): │ space label space │ + 1-cell gap.
    """
    out: list[tuple[int, int]] = []
    x = 2
    for i, item in enumerate(MENU):
        lw = len(_label(item))
        if i == _OTHERS_IDX:
            out.append((x + 2, lw))   # label starts after "│ "
            x += lw + 5               # │+space+label+space+│ + 1-cell gap
        else:
            out.append((x, lw))
            # 2-cell gap between consecutive normal items, 1-cell at group boundary
            next_i = i + 1
            gap = 2 if (next_i < len(MENU) and next_i != _OTHERS_IDX) else 1
            x += lw + gap
    return out


# ─── Rendering ────────────────────────────────────────────────────────────────

def _render_bar(total_w: int, focused: int, open_idx: int, dd_iw: int) -> "Text":
    """Render the 3-row horizontal menu bar as a Rich Text object.

    Row 1: top border  ────────┬────────┬────────
    Row 2: item labels  item1  │ item2 │  item3
    Row 3: bottom border  ┬──┬─┴────────┴────────
    """
    layout = _bar_layout()
    lx_o, lw_o = layout[_OTHERS_IDX]
    ox = lx_o - 2           # column of Others left  │
    oe = lx_o + lw_o + 1    # column of Others right │

    # ── Row 1: top border ────────────────────────────────────────────────────
    r1 = ["─"] * total_w
    if 0 <= ox < total_w:
        r1[ox] = "┬"
    if 0 <= oe < total_w:
        r1[oe] = "┬"

    # ── Row 2: item labels ───────────────────────────────────────────────────
    t2 = Text()
    pos = 0
    for i, item in enumerate(MENU):
        lx, lw = layout[i]
        label = _label(item)
        # Item is highlighted when it has focus (bar mode) or its dropdown is open
        hl = (i == open_idx) or (open_idx < 0 and i == focused)
        if i == _OTHERS_IDX:
            gap = (lx - 2) - pos
            if gap > 0:
                t2.append(" " * gap)
            if hl:
                t2.append("│", style=_S["lines"])
                t2.append(f" {label} ", style=_S["item_sel"])
                t2.append("│", style=_S["lines"])
            else:
                t2.append("│ ", style=_S["lines"])
                t2.append(label, style=_S["item"])
                t2.append(" │", style=_S["lines"])
            pos = lx + lw + 2
        else:
            gap = lx - pos
            if hl:
                if gap > 1:
                    t2.append(" " * (gap - 1))
                t2.append(f" {label} ", style=_S["item_sel"])
                pos = lx + lw + 1
            else:
                if gap > 0:
                    t2.append(" " * gap)
                t2.append(label, style=_S["item"])
                pos = lx + lw
    if pos < total_w:
        t2.append(" " * (total_w - pos))

    # ── Row 3: bottom border ─────────────────────────────────────────────────
    r3 = ["─"] * total_w
    if open_idx >= 0 and dd_iw > 0 and open_idx == _OTHERS_IDX:
        # ┴ closes the Others left │ connector; dropdown ┌ starts one cell to the right.
        # oe falls inside the dropdown span → stays "─" (no explicit write needed).
        dl = ox + 1                  # dropdown left corner = ox + 1
        dr = dl + dd_iw + 3         # dropdown right corner
        if 0 <= ox < total_w:
            r3[ox] = "┴"
        if 0 < dl < total_w:
            r3[dl] = "┌"
        if 0 < dr < total_w:
            r3[dr] = "┐"
    else:
        # No dropdown open, or non-Others dropdown: draw Others box bottom
        if 0 <= ox < total_w:
            r3[ox] = "┴"
        if 0 <= oe < total_w:
            r3[oe] = "┴"
        if open_idx >= 0 and dd_iw > 0:
            lx, _ = layout[open_idx]
            dl = lx - 1
            dr = dl + dd_iw + 3
            if 0 <= dl < total_w:
                r3[dl] = "┌"
            if 0 < dr < total_w:
                r3[dr] = "┐"

    result = Text()
    result.append("".join(r1), style=_S["lines"])
    result.append("\n")
    result.append_text(t2)
    result.append("\n")
    result.append("".join(r3), style=_S["lines"])
    return result


def _render_dropdown_body(items: list, cursor: int, iw: int) -> "Text":
    """First-level dropdown body: no top border (menu bar provides it)."""
    t = Text()
    sep = f"├{'─' * (iw + 2)}┤"
    bot = f"└{'─' * (iw + 2)}┘"
    for i, it in enumerate(items):
        if it is None:
            t.append(sep + "\n", style=_S["lines"])
            continue
        label = _label(it)
        cell = f"{label:<{iw - 2}} »" if _kids(it) is not None else f"{label:<{iw}}"
        if i == cursor:
            t.append("│", style=_S["lines"])
            t.append(f" {cell} ", style=_S["item_sel"])
            t.append("│\n", style=_S["lines"])
        else:
            t.append("│", style=_S["lines"])
            t.append(f" {cell} ", style=_S["item"])
            t.append("│\n", style=_S["lines"])
    t.append(bot, style=_S["lines"])
    return t


def _render_cascade(items: list, cursor: int, iw: int) -> "Text":
    """Cascading submenu that opens to the right of the parent item."""
    t = Text()
    top = f"┌{'─' * (iw + 2)}┐"
    sep = f"├{'─' * (iw + 2)}┤"
    bot = f"└{'─' * (iw + 2)}┘"
    t.append(top + "\n", style=_S["lines"])
    for i, it in enumerate(items):
        if it is None:
            t.append(sep + "\n", style=_S["lines"])
            continue
        label = _label(it)
        cell = f"{label:<{iw - 2}} »" if _kids(it) is not None else f"{label:<{iw}}"
        if i == cursor:
            t.append("│", style=_S["lines"])
            t.append(f" {cell} ", style=_S["item_sel"])
            t.append("│\n", style=_S["lines"])
        else:
            t.append("│", style=_S["lines"])
            t.append(f" {cell} ", style=_S["item"])
            t.append("│\n", style=_S["lines"])
    t.append(bot, style=_S["lines"])
    return t


# ─── Dialog renderer ──────────────────────────────────────────────────────────

def _render_dialog(
    breadcrumb: str,
    body_lines: list,
    buttons: list[str],
    btn_focus: int,
    width: int,
) -> "Text":
    """Render a WSL4AI dialog frame as Rich Text.

    Frame structure (width W, inner iw=W-2, content cw=W-6):
        ╔╣ breadcrumb ╠═══╗
        ║                 ║
        ║ +--content----+ ║
        ║ |             | ║  × body_lines
        ║ +-------------+ ║
        ╠═════════════════╣
        ║ +--buttons----+ ║
        ║ |       [ OK ]| ║
        ║ +-------------+ ║
        ╚═════════════════╝

    body_lines: list of str | list[tuple[str,style]]
    """
    L   = _S["lines"]
    T   = _S["text"]
    LBL = _S["label"]

    iw = width - 2      # inner width  (between ║ ║)
    cw = width - 4      # content width (1-space margin each side: ║ content ║)

    t = Text()

    # ── Header ────────────────────────────────────────────────────────────────
    bc   = f" {breadcrumb} "
    fill = max(0, width - 4 - len(bc))   # ╔╣ + bc + ╠ + fill + ╗ = width
    t.append("╔╣",        style=L)
    t.append(bc,          style=LBL)
    t.append("╠" + "═" * fill + "╗\n", style=L)

    # ── Body area ─────────────────────────────────────────────────────────────
    t.append("║" + " " * iw + "║\n", style=L)   # blank line above content

    for line in body_lines:
        if isinstance(line, str):
            padded = line[:cw].ljust(cw)
            t.append("║ ",   style=L)
            t.append(padded, style=T)
            t.append(" ║\n", style=L)
        else:
            # list/tuple of (chunk, style) pairs
            t.append("║ ", style=L)
            used = 0
            for chunk, sty in line:
                t.append(chunk, style=sty)
                used += len(chunk)
            if used < cw:
                t.append(" " * (cw - used))
            t.append(" ║\n", style=L)

    # ── Separator ─────────────────────────────────────────────────────────────
    t.append("╠" + "═" * iw + "╣\n", style=L)

    # ── Button row (right-aligned, equal width, 1-space gap between buttons) ─────
    max_bw = max(len(b) for b in buttons) if buttons else 0
    btn_chunks: list[tuple[str, str]] = []
    for i, btn in enumerate(buttons):
        cell = f" {btn.center(max_bw)} "          # equal width for all buttons
        sty  = _S["button_sel"] if i == btn_focus else _S["button"]
        btn_chunks.append((cell, sty))

    # total width = sum of cells + 1-space gap between each pair
    total_bw = sum(len(c) for c, _ in btn_chunks) + max(0, len(btn_chunks) - 1)
    t.append("║ ",                   style=L)
    t.append(" " * (cw - total_bw), style=T)
    for i, (cell, sty) in enumerate(btn_chunks):
        if i > 0:
            t.append(" ", style=T)          # 1-space gap between buttons
        t.append(cell, style=sty)
    t.append(" ║\n", style=L)

    # ── Footer ────────────────────────────────────────────────────────────────
    t.append("╚" + "═" * iw + "╝", style=L)

    return t


# ─── Data helpers ─────────────────────────────────────────────────────────────

def _lpad(label: str, width: int) -> str:
    """Pad label to `width` with spaces and append one separator space."""
    return label.ljust(width) + " "


def _row_fields(row: dict) -> dict:
    """Extract {key: value} dict from a row_from_pairs envelope row."""
    return {f["key"]: f["value"] for f in row.get("fields", [])}


_PROTECTED_ALIASES = {"wsl4ai"}  # cannot be removed


# ─── Widgets ──────────────────────────────────────────────────────────────────

if _HAS_TEXTUAL:

    class Banner(Widget):
        DEFAULT_CSS = """
        Banner {
            height: 5;
            width: 1fr;
        }
        """

        def render(self) -> "Text":
            w  = self.size.width or 80
            ri = None
            try:
                ri = self.app._cli_args.runtime_identity
            except Exception:
                pass

            t = Text()
            t.append("\n")   # top padding
            for i, (body, tent) in enumerate(zip(BANNER_BODY, BANNER_TENTACLES)):
                line = Text()
                line.append(" ")
                line.append(body, style=_BANNER_MAGENTA)
                line.append(tent, style=_S["lines"])

                prefix_len = 1 + len(body) + len(tent)   # " " + body + tentacles

                if i == 0:
                    # " WSL4AI " (label) + "v{version}" (text) — right-aligned together
                    app_part = " WSL4AI "
                    ver_part = f"v{_APP_VERSION}"
                    total    = len(app_part) + 1 + len(ver_part)
                    pad = max(0, w - prefix_len - total - 1)
                    line.append(" " * pad)
                    line.append(app_part, style=_S["label"])
                    line.append(" ")                          # neutral separator
                    line.append(ver_part, style=_S["text"])

                elif i == 1:
                    # github url (lines style)
                    pad = max(0, w - prefix_len - len(BANNER_GITHUB) - 1)
                    line.append(" " * pad)
                    line.append(BANNER_GITHUB, style=_S["lines"])

                elif i == 2:
                    pass   # blank line

                else:  # i == 3 — identity: user@wsl(machine)
                    if ri:
                        user    = ri.user     or ""
                        wsl     = ri.wsl_name or ""
                        machine = ri.machine  or ""
                        ident   = f"{user}@{wsl}({machine})"
                        pad = max(0, w - prefix_len - len(ident) - 1)
                        line.append(" " * pad)
                        line.append(user,    style=_S["text_hl"])
                        line.append("@",     style=_S["lines"])
                        line.append(wsl,     style=_S["text_hl"])
                        line.append("(",     style=_S["lines"])
                        line.append(machine, style=_S["text_hl"])
                        line.append(")",     style=_S["lines"])

                t.append_text(line)
                t.append("\n")
            return t

    class MenuBar(Widget):
        DEFAULT_CSS = """
        MenuBar {
            height: 3;
            width: 1fr;
        }
        """

        def render(self) -> "Text":
            w = self.size.width or 80
            a: "Wsl4aiApp" = self.app  # type: ignore[assignment]
            return _render_bar(w, a._bar_focus, a._open_top_idx, a._dd_iw)

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class DropdownMenu(Widget):
        """A vertical dropdown or cascading submenu panel."""

        DEFAULT_CSS = """
        DropdownMenu {
            layer: above;
            background: $surface;
            border: none;
        }
        """

        def __init__(self, items: list, x: int, y: int, cascade: bool = False) -> None:
            super().__init__()
            self._items = items
            self._x = x
            self._y = y           # absolute screen y (used for child cascade calculations)
            self._y_rel: int | None = None  # relative offset set by _push_cascade
            self._cascade = cascade
            self._cursor = next((i for i, it in enumerate(items) if it is not None), 0)

        def on_mount(self) -> None:
            iw = _dropdown_iw(self._items)
            extra = 1 if self._cascade else 0   # +1 row for top border in cascades
            self.styles.width = iw + 4          # │ + space + content + space + │
            self.styles.height = len(self._items) + 1 + extra
            # Use relative offset for cascades (natural flow pos ≠ 0 on above layer)
            offset_y = self._y_rel if self._y_rel is not None else self._y
            self.styles.offset = (self._x, offset_y)

        def render(self) -> "Text":
            iw = _dropdown_iw(self._items)
            if self._cascade:
                return _render_cascade(self._items, self._cursor, iw)
            return _render_dropdown_body(self._items, self._cursor, iw)

        def move(self, d: int) -> None:
            """Move cursor up (d=-1) or down (d=1), skipping separators."""
            n = len(self._items)
            i = self._cursor + d
            while 0 <= i < n:
                if self._items[i] is not None:
                    self._cursor = i
                    break
                i += d
            self.refresh()

        @property
        def current_item(self):
            return self._items[self._cursor] if 0 <= self._cursor < len(self._items) else None

        @property
        def iw(self) -> int:
            return _dropdown_iw(self._items)

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    from textual.screen import ModalScreen

    class _DialogWidget(Widget):
        """Renders the full dialog frame as Rich Text."""

        DEFAULT_CSS = """
        _DialogWidget { background: $surface; }
        """

        def __init__(self, dlg: "Wsl4aiDialog") -> None:
            super().__init__()
            self._dlg = dlg

        def on_mount(self) -> None:
            d = self._dlg
            self.styles.width  = d._dlg_w
            self.styles.height = d._height()

        def render(self) -> "Text":
            d = self._dlg
            return _render_dialog(
                d._breadcrumb, d.body_lines(), d._buttons, d._btn_focus, d._dlg_w
            )

    class Wsl4aiDialog(ModalScreen):
        """Base WSL4AI dialog.  Subclass and override body_lines()."""

        DEFAULT_CSS = """
        Wsl4aiDialog { align: center middle; }
        """

        def __init__(
            self,
            breadcrumb: str,
            width: int = 60,
            body_rows: int = 5,
            buttons: "list[str] | None" = None,
        ) -> None:
            super().__init__()
            self._breadcrumb = breadcrumb
            self._dlg_w      = width
            self._body_rows  = body_rows
            self._buttons    = buttons or ["Close"]
            self._btn_focus  = 0

        def _height(self) -> int:
            # header + blank + body_rows + separator + btn_row + footer
            return self._body_rows + 5

        def compose(self) -> ComposeResult:
            yield _DialogWidget(self)

        def body_lines(self) -> list:
            """Override to provide content. Return list of str or [(chunk,style),...]."""
            return [""] * self._body_rows

        def on_key(self, event: "events.Key") -> None:
            """Single on_key for the entire dialog hierarchy.

            Textual calls on_key for EVERY class in the MRO that defines it.
            By defining it ONLY here (not in subclasses) we guarantee it runs
            exactly once.  Subclasses override _handle_key() instead.
            """
            event.stop()
            self._handle_key(event)

        def _handle_key(self, event: "events.Key") -> None:
            """Override in subclasses to add extra key handling.
            Tab-based circular input navigation is for ADD dialogs only.
            """
            if event.key == "enter":
                self.dismiss(self._buttons[self._btn_focus])
            elif event.key == "escape":
                self.dismiss(None)

        def _refresh_dlg(self) -> None:
            try:
                self.query_one(_DialogWidget).refresh()
            except Exception:
                pass

    class ConfirmDialog(Wsl4aiDialog):
        """Simple confirmation dialog.  Esc=Cancel, Enter=Ok (no tab navigation)."""

        def __init__(self, message: str, width: int = 50) -> None:
            super().__init__(
                breadcrumb="Confirm",
                width=width,
                body_rows=3,
                buttons=["Cancel", "Ok"],
            )
            self._message = message
            self._btn_focus = 1   # highlight Ok

        def body_lines(self) -> list:
            cw = self._dlg_w - 4
            return [
                "",
                self._message[:cw].center(cw),
                "",
            ]

        def _handle_key(self, event: "events.Key") -> None:
            if event.key == "escape":
                self.dismiss(None)
            elif event.key == "enter":
                self.dismiss("Ok")

    class ListDialog(Wsl4aiDialog):
        """Scrollable multi-line record list dialog.

        Shows a fixed header line + separator, then a scrollable window of records.
        Each record is a list of display lines; records are separated by a blank row.
        The scrollbar on the right is proportional (thumb size reflects visible fraction).
        """

        def __init__(
            self,
            breadcrumb: str,
            header: str,
            records: "list[list[str]]",
            width: int = 78,
        ) -> None:
            self._header  = header
            self._records = records
            # Build flat list: (field_data, record_idx)
            # field_data = (label_str, value_str) for record lines, None for separators
            self._flat: "list[tuple[any, int]]" = []
            for ri, rec in enumerate(records):
                for field in rec:
                    self._flat.append((field, ri))
                if ri < len(records) - 1:
                    self._flat.append((None, -1))  # blank separator between records
            self._scroll = 0   # first visible flat line
            self._cursor = 0   # selected record index
            content_rows = min(14, max(3, len(self._flat)))
            # body_rows = header(1) + separator(1) + content rows
            super().__init__(breadcrumb, width=width, body_rows=content_rows + 2, buttons=["Close"])

        # ── proportional scrollbar ─────────────────────────────────────────────

        def _build_scrollbar(self, content_rows: int) -> "list[str]":
            """Return a list of content_rows characters for the scrollbar column.

            ▓ = thumb (visible region indicator)
            ░ = track (non-visible region)
            Thumb height is proportional to fraction visible.  When everything fits,
            the entire bar is ▓ (no scrolling needed).
            """
            n = len(self._flat)
            if n <= content_rows:
                return ["▓"] * content_rows          # everything fits — full thumb
            max_scroll = n - content_rows
            thumb_h    = max(1, round(content_rows * content_rows / n))
            thumb_h    = min(thumb_h, content_rows)
            track      = content_rows - thumb_h
            thumb_start = round(self._scroll / max_scroll * track) if track > 0 else 0
            thumb_start = max(0, min(thumb_start, track))
            return [
                "▓" if thumb_start <= i < thumb_start + thumb_h else "░"
                for i in range(content_rows)
            ]

        # ── rendering ─────────────────────────────────────────────────────────

        def body_lines(self) -> list:
            cw           = self._dlg_w - 4   # total content width (as per _render_dialog)
            tw           = cw - 1            # text width — last column is scrollbar
            content_rows = self._body_rows - 2
            result: list = []

            # ── header line (dynamic position counter) ───────────────────────
            # Count only real records (first field is a tuple, not a plain string)
            n_rec = sum(
                1 for r in self._records
                if r and not isinstance(r[0], str)
            )
            if n_rec > 0:
                pos_str = f"({self._cursor + 1}/{n_rec} entries)"
            else:
                pos_str = "(0 entries)"
            hdr_full = f"{self._header}  {pos_str}"
            result.append([(hdr_full[:tw].ljust(tw), _S["label"]), (" ", "")])

            # ── separator ─────────────────────────────────────────────────────
            result.append([("─" * tw, _S["lines"]), ("─", _S["lines"])])

            # ── content window ────────────────────────────────────────────────
            window    = self._flat[self._scroll : self._scroll + content_rows]
            scrollbar = self._build_scrollbar(content_rows)

            for i, (field, ri) in enumerate(window):
                is_sel   = (ri == self._cursor and ri >= 0)
                bar_char = scrollbar[i]
                if field is None:              # blank separator row
                    result.append([(" " * tw, _S["text"]), (bar_char, _S["lines"])])
                elif isinstance(field, str):   # plain-text message (e.g. "(no entries)")
                    sty = _S["item_sel"] if is_sel else _S["text"]
                    result.append([(field[:tw].ljust(tw), sty), (bar_char, _S["lines"])])
                elif is_sel:
                    # selected: flatten label+value, render as one highlighted block
                    lbl, val = field
                    full = (lbl + val)[:tw].ljust(tw)
                    result.append([(full, _S["item_sel"]), (bar_char, _S["lines"])])
                else:
                    # normal: label in text_hl, value in text
                    lbl, val = field
                    lbl_w = len(lbl)
                    val_w = max(0, tw - lbl_w)
                    result.append([
                        (lbl,                         _S["text_hl"]),
                        (val[:val_w].ljust(val_w),    _S["text"]),
                        (bar_char,                    _S["lines"]),
                    ])

            # ── pad empty rows ─────────────────────────────────────────────────
            while len(result) < self._body_rows:
                result.append("")

            return result

        # ── keyboard ──────────────────────────────────────────────────────────

        def _handle_key(self, event: "events.Key") -> None:
            if not self._navigate(event.key):
                super()._handle_key(event)

        def _navigate(self, key: str) -> bool:
            """Move cursor up/down. Returns True if handled."""
            n            = len(self._records)
            content_rows = self._body_rows - 2
            max_scroll   = max(0, len(self._flat) - content_rows)
            if key == "up" and self._cursor > 0:
                self._cursor -= 1
                self._ensure_visible(content_rows, max_scroll)
                self._refresh_dlg()
                return True
            if key == "down" and self._cursor < n - 1:
                self._cursor += 1
                self._ensure_visible(content_rows, max_scroll)
                self._refresh_dlg()
                return True
            return False

        def _ensure_visible(self, content_rows: int, max_scroll: int) -> None:
            """Scroll so ALL lines of the selected record are visible if possible."""
            indices = [i for i, (_, ri) in enumerate(self._flat) if ri == self._cursor]
            if not indices:
                return
            first, last = indices[0], indices[-1]
            if first < self._scroll:
                # record is above — scroll up to first line
                self._scroll = first
            elif last >= self._scroll + content_rows:
                # record is below (or partially) — scroll down so last line is visible
                self._scroll = min(max_scroll, last - content_rows + 1)
            self._scroll = max(0, min(self._scroll, max_scroll))

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class RegistryRemoveDialog(ListDialog):
        """Registry Remove — list view with Cancel/Remove buttons."""

        def __init__(self, breadcrumb: str) -> None:
            from commands.interface import interface_registry_list
            from commands.tui_decorator import registry_list_records
            env = interface_registry_list()
            hdr, recs = registry_list_records(env)
            super().__init__(breadcrumb, hdr, recs, width=80)
            self._buttons    = ["Cancel", "Remove"]
            self._btn_focus  = 0
            from commands.interface import rows_of
            self._env_rows   = rows_of(env)

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            if key == "escape":
                self.dismiss(None)
            elif key == "enter":
                if not self._env_rows or self._cursor >= len(self._env_rows):
                    return
                f = _row_fields(self._env_rows[self._cursor])
                self._confirm_remove(f.get("registryUuid", ""), f.get("registryName", ""))
            else:
                self._navigate(key)

        def _confirm_remove(self, uuid: str, name: str) -> None:
            from commands.common import DB_PATH, connect_db
            from commands.wsl_db import count_uses_for_registry
            try:
                with connect_db(DB_PATH) as con:
                    n_use = count_uses_for_registry(con, uuid)
            except Exception as exc:
                _notify_err(self.app, f"Error: {exc}")
                return
            if n_use > 0:
                _notify_err(self.app, f"Cannot remove '{name}': still has use links")
                return

            def _do_remove(result: "str | None") -> None:
                if result != "Ok":
                    return
                from commands.interface import interface_registry_remove, message_of, status_of
                env = interface_registry_remove(registry_uuid=uuid)
                if status_of(env) == 0:
                    self.app.notify(f"Removed registry: {name}", timeout=3)
                    self.dismiss(None)
                else:
                    _notify_err(self.app, f"Remove failed: {message_of(env)}")

            self.app.push_screen(ConfirmDialog(f"Remove '{name}'?"), _do_remove)

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class WslSetFormDialog(Wsl4aiDialog):
        """Edit the CLI command for a single WSL entry (pre-filled)."""

        # read-only context labels (padded to "CLI cmd" = 7 chars)
        _LABELS_RO = ["UUID   ", "Name   ", "User   "]
        _LW        = 7    # label display width
        _LBL_EDIT  = "CLI cmd"                           # editable label, 7 chars

        def __init__(self, breadcrumb: str, uuid: str, name: str, user: str, cli_cmd: str) -> None:
            # NOTE: avoid self._name — Textual's Widget uses it internally
            self._wsl_uuid = uuid
            self._wsl_name = name
            self._wsl_user = user
            # body: blank + 3 ro + blank + 1 editable + blank = 7 rows
            super().__init__(breadcrumb, width=70, body_rows=7, buttons=["Cancel", "Save"])
            self._cli_val        = cli_cmd or ""   # pre-filled
            self._cursor_visible = True
            self._blink_timer    = None

        def on_mount(self) -> None:
            self._blink_timer = self.set_interval(0.5, self._blink)

        def on_unmount(self) -> None:
            if self._blink_timer:
                self._blink_timer.stop()

        def _blink(self) -> None:
            self._cursor_visible = not self._cursor_visible
            self._refresh_dlg()

        def body_lines(self) -> list:
            cw = self._dlg_w - 4
            iw = cw - self._LW - 2   # value width

            result: list = [""]   # blank

            # read-only context rows
            for lbl, val in zip(self._LABELS_RO, [self._wsl_uuid, self._wsl_name, self._wsl_user]):
                safe = (val or "")
                result.append([(lbl + "  ", _S["text_hl"]), (safe[:iw].ljust(iw), _S["text"])])

            result.append("")   # blank separator

            # editable CLI cmd field
            val     = self._cli_val
            visible = val[-(iw - 1):] if len(val) >= iw else val
            cursor  = "│" if self._cursor_visible else " "
            display = (visible + cursor).ljust(iw)
            result.append([(self._LBL_EDIT + "  ", _S["text_hl"]), (display, _S["input_sel"])])

            result.append("")   # blank
            return result

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            if key == "escape":
                self.dismiss(None)
            elif key == "backspace":
                if self._cli_val:
                    self._cli_val = self._cli_val[:-1]
                    self._refresh_dlg()
            elif key == "enter":
                self._try_save()
            elif event.is_printable and event.character:
                self._cli_val += event.character
                self._refresh_dlg()

        def _try_save(self) -> None:
            cli_val = self._cli_val.strip()
            if not cli_val:
                self.app.notify("CLI cmd cannot be empty", timeout=3)
                return

            def _do_save(result: "str | None") -> None:
                if result != "Ok":
                    return
                from commands.interface import interface_wsl_set, message_of, status_of
                env = interface_wsl_set(cli_val, wsl_uuid=self._wsl_uuid)
                if status_of(env) == 0:
                    self.app.notify(f"Updated CLI cmd for '{self._wsl_name}'", timeout=3)
                    self.dismiss(None)
                else:
                    _notify_err(self.app, f"Save failed: {message_of(env)}")

            self.app.push_screen(ConfirmDialog(f"Save CLI cmd for '{self._wsl_name}'?"), _do_save)

    class WslSetDialog(ListDialog):
        """Select a WSL entry to edit its CLI command."""

        def __init__(self, breadcrumb: str) -> None:
            from commands.interface import interface_wsl_list, rows_of
            from commands.tui_decorator import wsl_list_records
            env = interface_wsl_list()
            hdr, recs = wsl_list_records(env)
            super().__init__(breadcrumb, hdr, recs)
            self._buttons   = ["Cancel", "Set"]
            self._btn_focus = 0
            self._env_rows  = rows_of(env)

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            if key == "escape":
                self.dismiss(None)
            elif key == "enter":
                if not self._env_rows or self._cursor >= len(self._env_rows):
                    return
                f = _row_fields(self._env_rows[self._cursor])
                uuid    = f.get("wslUuid", "")
                name    = f.get("wslName", "")
                user    = f.get("wslUser", "")
                cli_cmd = f.get("cliCommand", "")
                if cli_cmd == "<unset>":
                    cli_cmd = ""
                self.app.push_screen(
                    WslSetFormDialog(f"Wsl > Set > {name}", uuid, name, user, cli_cmd),
                    lambda _: None,
                )
            elif key in ("up", "down"):
                n            = len(self._records)
                content_rows = self._body_rows - 2
                max_scroll   = max(0, len(self._flat) - content_rows)
                if key == "up" and self._cursor > 0:
                    self._cursor -= 1
                    self._ensure_visible(content_rows, max_scroll)
                    self._refresh_dlg()
                elif key == "down" and self._cursor < n - 1:
                    self._cursor += 1
                    self._ensure_visible(content_rows, max_scroll)
                    self._refresh_dlg()

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class RegistryAddDialog(Wsl4aiDialog):
        """Registry Add form — Name / Host / Wsl inputs with Tab circular navigation."""

        _LW = 14   # "Path Base Host" / "Path Base Wsl "

        def __init__(self, breadcrumb: str, width: int = 68) -> None:
            # body: blank + Name + Path Base Host + Path Host + Path Base Wsl + Path Wsl + blank = 7
            super().__init__(breadcrumb, width=width, body_rows=7, buttons=["Cancel", "Add"])
            self._values         = ["", "", ""]   # Name, rel_path_host, rel_path_wsl
            self._field_focus    = 0              # active input index (0-2)
            self._cursor_visible = True
            self._blink_timer    = None
            from commands.common import expand_path_template, load_local_env_paths
            bh, bw = load_local_env_paths()
            base_host, base_wsl = expand_path_template(bh), expand_path_template(bw)
            self._base_host      = base_host
            self._base_wsl       = base_wsl

        def on_mount(self) -> None:
            self._blink_timer = self.set_interval(0.5, self._blink)

        def on_unmount(self) -> None:
            if self._blink_timer:
                self._blink_timer.stop()

        def _blink(self) -> None:
            self._cursor_visible = not self._cursor_visible
            self._refresh_dlg()

        # ── rendering ─────────────────────────────────────────────────────────

        def _input_row(self, field_idx: int, label: str, val: str, iw: int) -> list:
            active  = (field_idx == self._field_focus)
            visible = val[-(iw - 1):] if len(val) >= iw else val
            if active:
                cursor_char = "│" if self._cursor_visible else " "
                display = (visible + cursor_char).ljust(iw)
                return [(label.ljust(self._LW) + "  ", _S["text_hl"]),
                        (display,                       _S["input_sel"])]
            display = visible.ljust(iw)
            return [(label.ljust(self._LW) + "  ", _S["text"]),
                    (display,                       _S["input"])]

        def body_lines(self) -> list:
            cw = self._dlg_w - 4          # content width
            iw = cw - self._LW - 2        # input width
            result: list = [""]           # blank line above fields
            result.append(self._input_row(0, "Name", self._values[0], iw))
            result.append([
                (("Path Host Base").ljust(self._LW) + "  ", _S["text"]),
                (self._base_host,                           _S["text"]),
            ])
            result.append(self._input_row(1, "Path Host", self._values[1], iw))
            result.append([
                (("Path Wsl Base").ljust(self._LW) + "  ",  _S["text"]),
                (self._base_wsl,                            _S["text"]),
            ])
            result.append(self._input_row(2, "Path Wsl", self._values[2], iw))
            result.append("")             # blank line below fields
            return result

        # ── keyboard ──────────────────────────────────────────────────────────

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            n   = len(self._values)

            if key == "escape":
                self.dismiss(None)
            elif key == "down":
                self._field_focus = (self._field_focus + 1) % n
                self._refresh_dlg()
            elif key == "up":
                self._field_focus = (self._field_focus - 1) % n
                self._refresh_dlg()
            elif key == "backspace":
                if self._values[self._field_focus]:
                    self._values[self._field_focus] = self._values[self._field_focus][:-1]
                    self._refresh_dlg()
            elif key == "enter":
                self._try_submit()
            elif event.is_printable and event.character:
                self._values[self._field_focus] += event.character
                self._refresh_dlg()

        def _try_submit(self) -> None:
            name = self._values[0].strip()
            host = self._values[1].strip()
            wsl  = self._values[2].strip()
            if not name or not host or not wsl:
                self.app.notify("All fields are required", timeout=3)
                return
            from commands.interface import interface_registry_add, message_of, status_of
            env = interface_registry_add(name, host, wsl)
            if status_of(env) == 0:
                self.app.notify(f"Registry added: {name}", timeout=3)
                self.dismiss(None)
            else:
                _notify_err(self.app, message_of(env))

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class WhoAmIDialog(Wsl4aiDialog):
        """Display current runtime identity (machine, user, WSL name)."""

        _LABELS = ["Machine ", "User    ", "WSL Name"]  # padded to 8 chars
        _LW     = 8

        def __init__(self, breadcrumb: str, machine: str, user: str, wsl_name: str) -> None:
            super().__init__(breadcrumb, width=60, body_rows=5, buttons=["Close"])
            self._machine  = machine
            self._user     = user
            self._wsl_name = wsl_name

        def body_lines(self) -> list:
            cw = self._dlg_w - 4
            iw = cw - self._LW - 2
            result: list = [""]
            for lbl, val in zip(self._LABELS, [self._machine, self._user, self._wsl_name]):
                result.append([(lbl + "  ", _S["text_hl"]), ((val or "")[:iw].ljust(iw), _S["text"])])
            result.append("")
            return result

        def _handle_key(self, event: "events.Key") -> None:
            if event.key in ("escape", "enter"):
                self.dismiss(None)

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class UseAddDialog(ListDialog):
        """Select a registry to add a use link for the current WSL."""

        def __init__(self, breadcrumb: str, wsl_name: str, user: str) -> None:
            self._wsl_name = wsl_name
            self._user     = user
            from commands.interface import interface_registry_list_available, rows_of
            from commands.tui_decorator import registry_available_records
            env = interface_registry_list_available(wsl_name, user)
            hdr, recs = registry_available_records(env)
            super().__init__(breadcrumb, hdr, recs, width=80)
            self._buttons   = ["Cancel", "Add"]
            self._btn_focus = 0
            self._env_rows  = rows_of(env)

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            if key == "escape":
                self.dismiss(None)
            elif key == "enter":
                if not self._env_rows or self._cursor >= len(self._env_rows):
                    return
                f = _row_fields(self._env_rows[self._cursor])
                self._do_add(f.get("registryUuid", ""), f.get("registryName", ""))
            else:
                self._navigate(key)

        def _do_add(self, r_uuid: str, r_name: str) -> None:
            ri = self.app._cli_args.runtime_identity
            from commands.interface import interface_use_add, message_of, status_of
            env = interface_use_add(
                registry_uuid=r_uuid,
                wsl_name=ri.wsl_name,
                user=ri.user,
                runtime_wsl_name=ri.wsl_name,
            )
            if status_of(env) == 0:
                self.app.notify(f"Use added: {r_name}", timeout=3)
                self.dismiss(None)
            else:
                _notify_err(self.app, message_of(env))

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class UseRemoveDialog(ListDialog):
        """Select a use link to remove (filtered to current WSL)."""

        def __init__(self, breadcrumb: str, wsl_name: str, user: str) -> None:
            from commands.interface import interface_use_list, rows_of
            from commands.tui_decorator import use_list_records
            env = interface_use_list(
                wsl_uuid="", wsl_name=wsl_name, user=user,
                runtime_wsl_name=wsl_name, use_all=False, mounted_filter=None,
            )
            hdr, recs = use_list_records(env)
            super().__init__(breadcrumb, hdr, recs, width=80)
            self._buttons   = ["Cancel", "Remove"]
            self._btn_focus = 0
            self._env_rows  = rows_of(env)

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            if key == "escape":
                self.dismiss(None)
            elif key == "enter":
                if not self._env_rows or self._cursor >= len(self._env_rows):
                    return
                f = _row_fields(self._env_rows[self._cursor])
                r_uuid  = f.get("registryUuid", "")
                r_name  = f.get("registryName", "")
                w_uuid  = f.get("wslUuid", "")
                mounted = f.get("mounted", "0")
                if mounted == "1":
                    _notify_err(self.app, f"Cannot remove: '{r_name}' is mounted")
                    return
                self._confirm_remove(r_uuid, r_name, w_uuid)
            else:
                self._navigate(key)

        def _confirm_remove(self, r_uuid: str, r_name: str, w_uuid: str) -> None:
            def _do_remove(result: "str | None") -> None:
                if result != "Ok":
                    return
                from commands.interface import interface_use_remove, message_of, status_of
                env = interface_use_remove(r_uuid, w_uuid)
                if status_of(env) == 0:
                    self.app.notify(f"Removed use: {r_name}", timeout=3)
                    self.dismiss(None)
                else:
                    _notify_err(self.app, message_of(env))

            self.app.push_screen(ConfirmDialog(f"Remove use for '{r_name}'?"), _do_remove)

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class _UseToggleDialog(ListDialog):
        """Base for Enable/Disable: shows uses filtered by target mounted state."""

        _TARGET_MOUNTED: int = 0
        _NEW_MOUNTED:    int = 1
        _ACTION_LABEL:   str = "Enable"

        def __init__(self, breadcrumb: str, wsl_name: str, user: str) -> None:
            from commands.interface import interface_use_list, rows_of
            from commands.tui_decorator import use_list_records
            env = interface_use_list(
                wsl_uuid="", wsl_name=wsl_name, user=user,
                runtime_wsl_name=wsl_name, use_all=False,
                mounted_filter=self._TARGET_MOUNTED,
            )
            hdr, recs = use_list_records(env)
            super().__init__(breadcrumb, hdr, recs, width=80)
            self._buttons   = ["Cancel", self._ACTION_LABEL]
            self._btn_focus = 0
            self._env_rows  = rows_of(env)

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            if key == "escape":
                self.dismiss(None)
            elif key == "enter":
                if not self._env_rows or self._cursor >= len(self._env_rows):
                    return
                f = _row_fields(self._env_rows[self._cursor])
                self._confirm_toggle(
                    f.get("registryUuid", ""),
                    f.get("registryName", ""),
                    f.get("wslUuid", ""),
                )
            else:
                self._navigate(key)

        def _confirm_toggle(self, r_uuid: str, r_name: str, w_uuid: str) -> None:
            action = self._ACTION_LABEL.lower()

            def _do_toggle(result: "str | None") -> None:
                if result != "Ok":
                    return
                from commands.interface import (
                    interface_use_disable, interface_use_enable, message_of, status_of,
                )
                fn = interface_use_enable if self._NEW_MOUNTED == 1 else interface_use_disable
                env = fn(r_uuid, w_uuid)
                if status_of(env) == 0:
                    self.app.notify(f"{self._ACTION_LABEL}d: {r_name}", timeout=3)
                    self.dismiss(None)
                else:
                    _notify_err(self.app, message_of(env))

            self.app.push_screen(
                ConfirmDialog(f"{self._ACTION_LABEL} use for '{r_name}'?"),
                _do_toggle,
            )

    class UseEnableDialog(_UseToggleDialog):
        _TARGET_MOUNTED = 0
        _NEW_MOUNTED    = 1
        _ACTION_LABEL   = "Enable"

    class UseDisableDialog(_UseToggleDialog):
        _TARGET_MOUNTED = 1
        _NEW_MOUNTED    = 0
        _ACTION_LABEL   = "Disable"

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class AliasListDialog(ListDialog):
        """Show aliases with Name / Type fields."""

        def __init__(self, breadcrumb: str) -> None:
            from commands.interface import interface_alias_list
            from commands.tui_decorator import alias_list_records
            hdr, recs = alias_list_records(interface_alias_list())
            super().__init__(breadcrumb, hdr, recs)

        def _handle_key(self, event: "events.Key") -> None:
            if not self._navigate(event.key):
                if event.key in ("escape", "enter"):
                    self.dismiss(None)

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class AliasAddDialog(Wsl4aiDialog):
        """Add a new alias to ~/.startup-wsl4ai.sh."""

        _LBL  = "Alias name"
        _LW   = 10

        def __init__(self, breadcrumb: str) -> None:
            super().__init__(breadcrumb, width=56, body_rows=3, buttons=["Cancel", "Add"])
            self._value          = ""
            self._cursor_visible = True
            self._blink_timer    = None

        def on_mount(self) -> None:
            self._blink_timer = self.set_interval(0.5, self._blink)

        def on_unmount(self) -> None:
            if self._blink_timer:
                self._blink_timer.stop()

        def _blink(self) -> None:
            self._cursor_visible = not self._cursor_visible
            self._refresh_dlg()

        def body_lines(self) -> list:
            cw = self._dlg_w - 4
            iw = cw - self._LW - 2
            visible = self._value[-(iw - 1):] if len(self._value) >= iw else self._value
            cursor  = "│" if self._cursor_visible else " "
            display = (visible + cursor).ljust(iw)
            return [
                [(self._LBL + "  ", _S["text_hl"]), (display, _S["input_sel"])],
                "",
                "",
            ]

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            if key == "escape":
                self.dismiss(None)
            elif key == "backspace":
                if self._value:
                    self._value = self._value[:-1]
                    self._refresh_dlg()
            elif key == "enter":
                self._try_submit()
            elif event.is_printable and event.character:
                self._value += event.character
                self._refresh_dlg()

        def _try_submit(self) -> None:
            name = self._value.strip()
            if not name:
                self.app.notify("Alias name cannot be empty", timeout=3)
                return
            if name in _PROTECTED_ALIASES:
                _notify_err(self.app, f"'{name}' is a protected alias")
                return
            from commands.interface import interface_alias_add, message_of, status_of
            env = interface_alias_add([name])
            if status_of(env) == 0:
                self.app.notify(f"Alias added: {name}", timeout=3)
                self.dismiss(None)
            else:
                _notify_err(self.app, message_of(env))

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class AliasRemoveDialog(ListDialog):
        """Select an alias to remove. Shows Name / Type. Protected aliases blocked."""

        def __init__(self, breadcrumb: str) -> None:
            from commands.interface import interface_alias_list, rows_of
            from commands.tui_decorator import alias_list_records
            env = interface_alias_list()
            hdr, recs = alias_list_records(env)
            super().__init__(breadcrumb, hdr, recs)
            self._buttons   = ["Cancel", "Remove"]
            self._btn_focus = 0
            self._env_rows  = rows_of(env)

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            if key == "escape":
                self.dismiss(None)
            elif key == "enter":
                if not self._env_rows or self._cursor >= len(self._env_rows):
                    return
                f = _row_fields(self._env_rows[self._cursor])
                alias = f.get("name", "")
                if alias in _PROTECTED_ALIASES:
                    _notify_err(self.app, f"'{alias}' is a protected alias")
                    return
                self._confirm_remove(alias)
            else:
                self._navigate(key)

        def _confirm_remove(self, alias: str) -> None:
            def _do_remove(result: "str | None") -> None:
                if result != "Ok":
                    return
                from commands.interface import interface_alias_remove, message_of, status_of
                env = interface_alias_remove([alias])
                if status_of(env) == 0:
                    self.app.notify(f"Alias removed: {alias}", timeout=3)
                    self.dismiss(None)
                else:
                    _notify_err(self.app, message_of(env))

            self.app.push_screen(ConfirmDialog(f"Remove alias '{alias}'?"), _do_remove)

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class ThemeDialog(Wsl4aiDialog):
        """Theme picker with live preview on navigation.

        Navigating up/down applies the theme immediately (no save).
        Esc restores the original theme; Enter saves and closes.
        The current active theme is pre-selected on open.
        """

        def __init__(self, breadcrumb: str) -> None:
            W = max(len(name) for name, _ in _THEME_LIST)
            n = len(_THEME_LIST)
            super().__init__(breadcrumb, width=W + 10, body_rows=n + 2, buttons=["Cancel", "Apply"])
            self._original_id = _current_theme_id()
            # pre-select active theme
            ids = [tid for _, tid in _THEME_LIST]
            self._cursor = ids.index(self._original_id) if self._original_id in ids else 0
            self._btn_focus = 1   # Apply highlighted by default

        def body_lines(self) -> list:
            cw = self._dlg_w - 4
            result: list = [""]
            for i, (name, _tid) in enumerate(_THEME_LIST):
                cell = name.ljust(cw)
                sty  = _S["item_sel"] if i == self._cursor else _S["item"]
                result.append([(cell, sty)])
            result.append("")
            return result

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            n   = len(_THEME_LIST)
            if key == "up" and self._cursor > 0:
                self._cursor -= 1
                self._preview()
            elif key == "down" and self._cursor < n - 1:
                self._cursor += 1
                self._preview()
            elif key == "escape":
                # restore original theme without saving
                _save_theme(self._original_id)
                _load_theme()
                self.app._apply_theme()
                self.dismiss(None)
            elif key == "enter":
                # already applied; just save and close
                _save_theme(_THEME_LIST[self._cursor][1])
                self.dismiss(None)

        def _preview(self) -> None:
            """Apply theme visually (no save) and refresh dialog + app."""
            tid = _THEME_LIST[self._cursor][1]
            _save_theme(tid)          # write config so _load_theme reads it
            _load_theme()
            self.app._apply_theme()
            self._refresh_dlg()

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class StartDialog(ListDialog):
        """Select a mounted use to start."""

        def __init__(self, breadcrumb: str, header: str, records: list, raw_rows: list) -> None:
            # raw_rows: list of (r_uuid, r_name, rel_path_host, rel_path_wsl, cli_cmd)
            super().__init__(breadcrumb, header, records, width=78)
            self._buttons   = ["Cancel", "Start"]
            self._btn_focus = 0
            self._raw_rows  = raw_rows

        def _handle_key(self, event: "events.Key") -> None:
            key = event.key
            if key == "escape":
                self.dismiss(None)
            elif key == "enter":
                if not self._raw_rows or self._cursor >= len(self._raw_rows):
                    return
                self.dismiss(self._raw_rows[self._cursor])
            else:
                self._navigate(key)

    # ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──

    class Wsl4aiApp(App):
        """WSL4AI main Textual application."""

        CSS = """
        Screen {
            layers: default above;
        }
        """

        def __init__(self, cli_args: Namespace) -> None:
            super().__init__()
            self._cli_args = cli_args
            self._bar_focus: int = 0
            self._open_top_idx: int = -1
            self._dd_iw: int = 0
            self._stack: list[DropdownMenu] = []
            self._pending_start: "dict | None" = None   # set by StartDialog on selection

        def on_mount(self) -> None:
            target = "textual-light" if not _THEME_DARK else "textual-dark"
            logging.debug("on_mount: _THEME_DARK=%s  setting theme=%s", _THEME_DARK, target)
            self.theme = target
            logging.debug("on_mount: self.theme after set=%s  current_theme.dark=%s", self.theme, self.current_theme.dark)

        def compose(self) -> ComposeResult:
            yield Banner()
            yield MenuBar()

        def on_key(self, event: events.Key) -> None:
            if len(self.screen_stack) > 1:
                return   # modal is active — let it handle all keys
            if self._stack:
                self._key_dropdown(event.key)
            else:
                self._key_bar(event.key)

        # ── bar navigation ────────────────────────────────────────────────────

        def _key_bar(self, key: str) -> None:
            n = len(MENU)
            if key == "left":
                if self._bar_focus > 0:
                    self._bar_focus -= 1
                    self._refresh_bar()
            elif key == "right":
                if self._bar_focus < n - 1:
                    self._bar_focus += 1
                    self._refresh_bar()
            elif key == "down":
                if _kids(MENU[self._bar_focus]) is not None:
                    self._open_from_bar(self._bar_focus)
            elif key == "enter":
                self._open_from_bar(self._bar_focus)
            elif key == "escape":
                self._dispatch(["Exit"])

        def _open_from_bar(self, idx: int) -> None:
            item = MENU[idx]
            kids = _kids(item)
            if kids is None:
                self._dispatch([_label(item)])
                return
            layout = _bar_layout()
            lx, _ = layout[idx]
            x = lx - 1   # dropdown left │ aligns with bar ┌ (ox+1 for Others, lx-1 for all)
            dd = DropdownMenu(kids, x, 8, cascade=False)  # 5 banner rows + 3 bar rows
            self._open_top_idx = idx
            self._dd_iw = dd.iw
            self._stack = [dd]
            self._refresh_bar()
            self.screen.mount(dd)

        # ── dropdown navigation ───────────────────────────────────────────────

        def _key_dropdown(self, key: str) -> None:
            top = self._stack[-1]
            if key == "up":
                first = next((i for i, it in enumerate(top._items) if it is not None), 0)
                if len(self._stack) == 1 and top._cursor == first:
                    self._pop()   # first level, first item → close, back to bar
                else:
                    top.move(-1)
            elif key == "down":
                top.move(1)
            elif key == "enter":
                item = top.current_item
                if item is None:
                    return
                kids = _kids(item)
                if kids:
                    self._push_cascade(top, kids)
                else:
                    path = self._path() + [_label(item)]
                    self._dismiss_all()
                    self._dispatch(path)
            elif key == "right":
                item = top.current_item
                if item is not None and _kids(item) is not None:
                    self._push_cascade(top, _kids(item))   # open child cascade
                else:
                    self._navigate_bar_from_dropdown(1)    # any leaf (any depth) → bar right
            elif key == "left":
                if len(self._stack) > 1:
                    self._pop()                             # in cascade → close, back to parent
                else:
                    self._navigate_bar_from_dropdown(-1)   # first level → bar left
            elif key == "escape":
                self._pop()
            elif key == "q":
                self.exit()

        def _push_cascade(self, parent: "DropdownMenu", kids: list) -> None:
            # x: parent's right │ column — cascade overwrites it with ├
            x = parent._x + parent.iw + 3
            # y_abs: absolute screen row for the cascade top border
            extra = 1 if parent._cascade else 0
            y_abs = parent._y + extra + parent._cursor
            # y_rel: offset relative to cascade's natural flow position on the above layer.
            # Natural y = sum of heights of all already-mounted above-layer widgets.
            natural_y = sum(len(dd._items) + 1 + (1 if dd._cascade else 0) for dd in self._stack)
            y_rel = y_abs - natural_y
            logging.debug("_push_cascade: y_abs=%d  natural_y=%d  y_rel=%d  x=%d", y_abs, natural_y, y_rel, x)
            dd = DropdownMenu(kids, x, y_abs, cascade=True)
            dd._y_rel = y_rel
            self._stack.append(dd)
            self.screen.mount(dd)

        def _pop(self) -> None:
            if not self._stack:
                return
            self._stack.pop().remove()
            if not self._stack:
                self._open_top_idx = -1
                self._dd_iw = 0
                self._refresh_bar()

        def _dismiss_all(self) -> None:
            for dd in self._stack:
                dd.remove()
            self._stack.clear()
            self._open_top_idx = -1
            self._dd_iw = 0
            self._refresh_bar()

        def _navigate_bar_from_dropdown(self, direction: int) -> None:
            """Close all dropdowns, move bar focus left/right (non-circular), open new submenu."""
            new_focus = self._bar_focus + direction
            n = len(MENU)
            if new_focus < 0 or new_focus >= n:
                return  # boundary: do nothing, stay in current submenu
            self._dismiss_all()
            self._bar_focus = new_focus
            if _kids(MENU[self._bar_focus]) is not None:
                self._open_from_bar(self._bar_focus)
            else:
                self._refresh_bar()   # leaf item — just focus on bar, no dispatch

        def _path(self) -> list[str]:
            """Build the action path from root to the currently selected item."""
            path: list[str] = []
            if self._open_top_idx >= 0:
                path.append(_label(MENU[self._open_top_idx]))
            for dd in self._stack[:-1]:
                if dd.current_item is not None:
                    path.append(_label(dd.current_item))
            return path

        def _dispatch(self, path: list[str]) -> None:
            action     = " > ".join(path)
            breadcrumb = action
            if action == "Exit":
                def _on_confirm(result: "str | None") -> None:
                    if result == "Ok":
                        self.exit()
                self.push_screen(ConfirmDialog("Are you sure you want to exit?"), _on_confirm)
                return

            # ── Theme dialog ───────────────────────────────────────────────────
            if path == ["Others", "Theme"]:
                self.push_screen(ThemeDialog(breadcrumb))
                return

            # ── List dialogs ───────────────────────────────────────────────────
            if path == ["Registry", "List"]:
                from commands.interface import interface_registry_list
                from commands.tui_decorator import registry_list_records
                hdr, recs = registry_list_records(interface_registry_list())
                self.push_screen(ListDialog(breadcrumb, hdr, recs, width=80))
                return
            if path == ["Registry", "Remove"]:
                self.push_screen(RegistryRemoveDialog(breadcrumb))
                return
            if path == ["Registry", "Add"]:
                self.push_screen(RegistryAddDialog(breadcrumb))
                return
            if path[0] == "Use":
                ri = self._cli_args.runtime_identity
                wn, usr = ri.wsl_name, ri.user
                if path == ["Use", "List"]:
                    from commands.interface import interface_use_list
                    from commands.tui_decorator import use_list_records
                    env = interface_use_list(
                        wsl_uuid="", wsl_name=wn, user=usr,
                        runtime_wsl_name=wn, use_all=False, mounted_filter=None,
                    )
                    hdr, recs = use_list_records(env)
                    self.push_screen(ListDialog(breadcrumb, hdr, recs))
                    return
                if path == ["Use", "Add"]:
                    self.push_screen(UseAddDialog(breadcrumb, wn, usr))
                    return
                if path == ["Use", "Remove"]:
                    self.push_screen(UseRemoveDialog(breadcrumb, wn, usr))
                    return
                if path == ["Use", "Enable"]:
                    self.push_screen(UseEnableDialog(breadcrumb, wn, usr))
                    return
                if path == ["Use", "Disable"]:
                    self.push_screen(UseDisableDialog(breadcrumb, wn, usr))
                    return
            if path == ["Wsl", "List"]:
                from commands.interface import interface_wsl_list
                from commands.tui_decorator import wsl_list_records
                hdr, recs = wsl_list_records(interface_wsl_list())
                self.push_screen(ListDialog(breadcrumb, hdr, recs))
                return
            if path == ["Wsl", "Set"]:
                ri = self._cli_args.runtime_identity
                from commands.interface import interface_wsl_list, rows_of
                env = interface_wsl_list()
                env_rows = rows_of(env)
                row_match = next(
                    (r for r in env_rows
                     if _row_fields(r).get("wslName") == ri.wsl_name
                     and _row_fields(r).get("wslUser") == ri.user),
                    None,
                )
                if not row_match:
                    self.notify(
                        f"WSL '{ri.wsl_name}' not found in DB — run 'use add' first",
                        timeout=4,
                    )
                    return
                f = _row_fields(row_match)
                cli_cmd = f.get("cliCommand", "")
                if cli_cmd == "<unset>":
                    cli_cmd = ""
                self.push_screen(WslSetFormDialog(
                    breadcrumb,
                    f.get("wslUuid", ""),
                    f.get("wslName", "") or ri.wsl_name,
                    f.get("wslUser", "") or ri.user,
                    cli_cmd,
                ))
                return

            if path == ["Others", "Install", "Database"]:
                def _do_install_db(result: "str | None") -> None:
                    if result != "Ok":
                        return
                    from commands.interface import interface_install_database, message_of, status_of
                    env = interface_install_database(force=False)
                    if status_of(env) == 0:
                        self.notify(message_of(env), timeout=3)
                    else:
                        _notify_err(self, f"Database error: {message_of(env)}", timeout=5)
                self.push_screen(ConfirmDialog("Create database?"), _do_install_db)
                return

            if path == ["Others", "Install", "Alias", "List"]:
                self.push_screen(AliasListDialog(breadcrumb))
                return
            if path == ["Others", "Install", "Alias", "Add"]:
                self.push_screen(AliasAddDialog(breadcrumb))
                return
            if path == ["Others", "Install", "Alias", "Remove"]:
                self.push_screen(AliasRemoveDialog(breadcrumb))
                return

            if path == ["Start"]:
                ri = self._cli_args.runtime_identity
                from commands.interface import (
                    interface_start_prepare, interface_use_list_mounted, message_of, status_of,
                )
                env_prep = interface_start_prepare(ri.wsl_name, ri.user)
                if status_of(env_prep) != 0:
                    _notify_err(self, message_of(env_prep), timeout=5)
                    return
                env_mount = interface_use_list_mounted(ri.wsl_name, ri.user)
                if status_of(env_mount) != 0:
                    _notify_err(self, message_of(env_mount))
                    return
                raw_rows = env_mount.get("output", {}).get("data", {}).get("raw_rows", [])
                if not raw_rows:
                    _notify_err(self, "No mounted uses for current WSL")
                    return
                from commands.tui_decorator import use_list_mounted_records
                hdr, recs = use_list_mounted_records(env_mount)

                def _on_start(selected: "tuple | None") -> None:
                    if selected is None:
                        return
                    r_uuid, r_name, rel_path_host, rel_path, cli_cmd = selected
                    from commands.common import expand_path_template, load_local_env_paths
                    import os
                    cli = (cli_cmd or "").strip()
                    if not cli:
                        _notify_err(self, "CLI command is empty")
                        return
                    _, base_path_wsl = load_local_env_paths()
                    root = expand_path_template(str(base_path_wsl or ""))
                    if not root:
                        _notify_err(self, "Missing WSL_PROJECTS in local.env", timeout=5)
                        return
                    workdir = os.path.normpath(os.path.join(root, str(rel_path or "").strip()))
                    self._pending_start = {"cli": cli, "workdir": workdir, "name": r_name}
                    self.exit()

                self.push_screen(StartDialog(breadcrumb, hdr, recs, raw_rows), _on_start)
                return

            self.notify(f"→ {action}", timeout=3)

        def _apply_theme(self) -> None:
            """Switch Textual dark/light mode and refresh all widgets."""
            self.theme = "textual-light" if not _THEME_DARK else "textual-dark"
            try:
                self.query_one(Banner).refresh()
            except Exception:
                pass
            self._refresh_bar()

        def _refresh_bar(self) -> None:
            try:
                self.query_one(MenuBar).refresh()
            except Exception:
                pass


# ─── Entry point ──────────────────────────────────────────────────────────────

def cmd_tui(args: Namespace) -> int:
    """Launch the WSL4AI interactive Text User Interface."""
    import os
    import subprocess

    global _APP_VERSION
    if not _HAS_TEXTUAL:
        print("ERROR: textual is required; run pip install -r requirements.txt")
        return 1
    _configure_logging()
    _APP_VERSION = getattr(args, "app_version", "")
    _load_theme()
    app = Wsl4aiApp(args)
    app.run()

    pending = getattr(app, "_pending_start", None)
    if pending:
        cli     = pending["cli"]
        workdir = pending["workdir"]
        name    = pending.get("name", "")
        if not os.path.isdir(workdir):
            print(f"start: target directory not found: {workdir}")
            return 1
        print(f"Starting '{name}' in {workdir} …")
        try:
            proc = subprocess.run(cli, shell=True, cwd=workdir, check=False)
            return int(proc.returncode)
        except Exception as exc:
            print(f"start: execution failed: {exc}")
            return 1

    return 0
