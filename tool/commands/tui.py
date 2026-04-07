"""Textual-based Text User Interface for WSL4AI."""
from __future__ import annotations

import json
import logging
from argparse import Namespace
from pathlib import Path

_LOG = Path("/tmp/wsl4ai_tui.log")
logging.basicConfig(filename=_LOG, level=logging.DEBUG, format="%(asctime)s %(message)s", filemode="w")

try:
    from textual.app import App, ComposeResult
    from textual.widget import Widget
    from textual import events
    from rich.text import Text
    _HAS_TEXTUAL = True
except ImportError:
    _HAS_TEXTUAL = False


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
    try:
        data = json.loads((_THEMES_DIR / f"{theme_id}.json").read_text(encoding="utf-8"))
        raw = data.get("styles", {}) if isinstance(data, dict) else {}
    except Exception:
        pass
    # "dark" key is authoritative; fall back to name-based detection if missing
    if "dark" in raw:
        _THEME_DARK = bool(raw["dark"])
    else:
        _THEME_DARK = "light" not in theme_id.lower()
    logging.debug("_load_theme: theme_id=%s  dark_key_in_file=%r  _THEME_DARK=%s", theme_id, raw.get("dark", "MISSING"), _THEME_DARK)
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
    # item_sel: always the inverse of item (UX spec — not stored in theme)
    item = _S["item"]
    _S["item_sel"] = (item + " reverse").strip() if item else "bold reverse"
    # button_sel: explicit theme override or auto-invert from button
    if "button_sel" in raw:
        _S["button_sel"] = raw["button_sel"]
    else:
        btn = _S["button"]
        _S["button_sel"] = (btn + " reverse").strip() if btn else "bold reverse"


# ─── Menu definition ──────────────────────────────────────────────────────────
# str         → leaf action (direct dispatch on enter)
# (str, list) → item with submenu children
# None        → visual separator (only valid inside submenu lists)

MENU: list = [
    ("Registry", ["List", None, "Add", "Remove"]),
    ("Use", ["List", None, "Add", "Remove", None, "Enable", "Disable", "Disable All"]),
    ("Wsl", ["List", None, "Set"]),
    "Start",
    ("Others", [
        "Who Am I",
        None,
        ("Install", [
            "Tool",
            "Database",
            ("Alias", ["List", None, "Add", "Remove"]),
        ]),
        None,
        ("Theme", [
            ("Dark",  ["Normal", "Bright", "Color Blind"]),
            ("Light", ["Normal", "Bright", "Color Blind"]),
            "High Contrast",
        ]),
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
    if 0 <= ox < total_w:
        r3[ox] = "┴"
    if 0 <= oe < total_w:
        r3[oe] = "┴"
    if open_idx >= 0 and dd_iw > 0:
        lx, _ = layout[open_idx]
        dl = ox if open_idx == _OTHERS_IDX else lx - 1
        dr = dl + dd_iw + 3
        if 0 <= dl < total_w:
            r3[dl] = "┼" if open_idx == _OTHERS_IDX else "┬"
        if 0 < dr < total_w:
            r3[dr] = "┬"

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
        display = f"{label} »" if _kids(it) is not None else label
        cell = f"{display:<{iw}}"
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
    """Cascading submenu with connecting top border (├──...──┐)."""
    t = Text()
    top = f"├{'─' * (iw + 2)}┐"
    sep = f"├{'─' * (iw + 2)}┤"
    bot = f"└{'─' * (iw + 2)}┘"
    t.append(top + "\n", style=_S["lines"])
    for i, it in enumerate(items):
        if it is None:
            t.append(sep + "\n", style=_S["lines"])
            continue
        label = _label(it)
        display = f"{label} »" if _kids(it) is not None else label
        cell = f"{display:<{iw}}"
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


# ─── Widgets ──────────────────────────────────────────────────────────────────

if _HAS_TEXTUAL:

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
        }
        """

        def __init__(self, items: list, x: int, y: int, cascade: bool = False) -> None:
            super().__init__()
            self._items = items
            self._x = x
            self._y = y
            self._cascade = cascade
            self._cursor = next((i for i, it in enumerate(items) if it is not None), 0)

        def on_mount(self) -> None:
            iw = _dropdown_iw(self._items)
            extra = 1 if self._cascade else 0   # +1 row for top border in cascades
            self.styles.width = iw + 4          # │ + space + content + space + │
            self.styles.height = len(self._items) + 1 + extra
            self.styles.offset = (self._x, self._y)

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

        def on_mount(self) -> None:
            target = "textual-light" if not _THEME_DARK else "textual-dark"
            logging.debug("on_mount: _THEME_DARK=%s  setting theme=%s", _THEME_DARK, target)
            self.theme = target
            logging.debug("on_mount: self.theme after set=%s  current_theme.dark=%s", self.theme, self.current_theme.dark)

        def compose(self) -> ComposeResult:
            yield MenuBar()

        def on_key(self, event: events.Key) -> None:
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
            x = lx - 2 if idx == _OTHERS_IDX else lx - 1
            dd = DropdownMenu(kids, x, 3, cascade=False)
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
            # y: row of the currently selected item in parent
            extra = 1 if parent._cascade else 0
            y = parent._y + extra + parent._cursor
            dd = DropdownMenu(kids, x, y, cascade=True)
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
            action = " > ".join(path)
            if action == "Exit":
                self.exit()
                return
            # TODO: connect to command handlers in the next phase
            self.notify(f"→ {action}", timeout=3)

        def _refresh_bar(self) -> None:
            try:
                self.query_one(MenuBar).refresh()
            except Exception:
                pass


# ─── Entry point ──────────────────────────────────────────────────────────────

def cmd_tui(args: Namespace) -> int:
    """Launch the WSL4AI interactive Text User Interface."""
    if not _HAS_TEXTUAL:
        print("ERROR: textual is required; run pip install -r requirements.txt")
        return 1
    _load_theme()
    Wsl4aiApp(args).run()
    return 0
