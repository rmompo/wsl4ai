"""Textual-based Text User Interface for WSL4AI."""
from __future__ import annotations

from argparse import Namespace

try:
    from textual.app import App, ComposeResult
    from textual.widget import Widget
    from textual import events
    from rich.text import Text
    _HAS_TEXTUAL = True
except ImportError:
    _HAS_TEXTUAL = False


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
    - 1-cell left margin.
    - Normal items: label + 1-cell gap.
    - Others (boxed): │ space label space │ + 1-cell gap.
    """
    out: list[tuple[int, int]] = []
    x = 1
    for i, item in enumerate(MENU):
        lw = len(_label(item))
        if i == _OTHERS_IDX:
            out.append((x + 2, lw))   # label starts after "│ "
            x += lw + 5               # │+space+label+space+│ + 1-cell gap
        else:
            out.append((x, lw))
            x += lw + 1               # label + 1-cell gap
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
        if i == _OTHERS_IDX:
            gap = (lx - 2) - pos
            if gap > 0:
                t2.append(" " * gap)
            t2.append("│ ", style="dim")
            pos = lx
        else:
            gap = lx - pos
            if gap > 0:
                t2.append(" " * gap)
            pos = lx
        style = "bold reverse" if i == open_idx else ("bold" if i == focused else "")
        t2.append(label, style=style)
        pos += lw
        if i == _OTHERS_IDX:
            t2.append(" │", style="dim")
            pos += 2
    if pos < total_w:
        t2.append(" " * (total_w - pos))

    # ── Row 3: bottom border ─────────────────────────────────────────────────
    r3 = ["─"] * total_w
    # Others box: ┴ normally; ┼ when Others itself is open
    if 0 <= ox < total_w:
        r3[ox] = "┴"
    if 0 <= oe < total_w:
        r3[oe] = "┴"
    # Active dropdown opening
    if open_idx >= 0 and dd_iw > 0:
        lx, _ = layout[open_idx]
        dl = ox if open_idx == _OTHERS_IDX else lx - 1
        dr = dl + dd_iw + 3   # dl + │+space+content+space+│ - 1 = dl + iw+3
        if 0 <= dl < total_w:
            r3[dl] = "┼" if open_idx == _OTHERS_IDX else "┬"
        if 0 < dr < total_w:
            r3[dr] = "┬"

    result = Text()
    result.append("".join(r1), style="dim")
    result.append("\n")
    result.append_text(t2)
    result.append("\n")
    result.append("".join(r3), style="dim")
    return result


def _render_dropdown_body(items: list, cursor: int, iw: int) -> "Text":
    """First-level dropdown body: no top border (menu bar provides it)."""
    t = Text()
    sep = f"├{'─' * (iw + 2)}┤"
    bot = f"└{'─' * (iw + 2)}┘"
    for i, it in enumerate(items):
        if it is None:
            t.append(sep + "\n", style="dim")
            continue
        label = _label(it)
        display = f"{label} »" if _kids(it) is not None else label
        cell = f"{display:<{iw}}"
        if i == cursor:
            t.append("│", style="dim")
            t.append(f" {cell} ", style="bold reverse")
            t.append("│\n", style="dim")
        else:
            t.append("│", style="dim")
            t.append(f" {cell} ")
            t.append("│\n", style="dim")
    t.append(bot, style="dim")
    return t


def _render_cascade(items: list, cursor: int, iw: int) -> "Text":
    """Cascading submenu with connecting top border (├──...──┐)."""
    t = Text()
    top = f"├{'─' * (iw + 2)}┐"
    sep = f"├{'─' * (iw + 2)}┤"
    bot = f"└{'─' * (iw + 2)}┘"
    t.append(top + "\n", style="dim")
    for i, it in enumerate(items):
        if it is None:
            t.append(sep + "\n", style="dim")
            continue
        label = _label(it)
        display = f"{label} »" if _kids(it) is not None else label
        cell = f"{display:<{iw}}"
        if i == cursor:
            t.append("│", style="dim")
            t.append(f" {cell} ", style="bold reverse")
            t.append("│\n", style="dim")
        else:
            t.append("│", style="dim")
            t.append(f" {cell} ")
            t.append("│\n", style="dim")
    t.append(bot, style="dim")
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
                self._bar_focus = (self._bar_focus - 1) % n
                self._refresh_bar()
            elif key == "right":
                self._bar_focus = (self._bar_focus + 1) % n
                self._refresh_bar()
            elif key in ("enter", "down", "space"):
                self._open_from_bar(self._bar_focus)
            elif key == "q":
                self.exit()

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
                top.move(-1)
            elif key == "down":
                top.move(1)
            elif key in ("enter", "right"):
                item = top.current_item
                if item is None:
                    return
                kids = _kids(item)
                if kids:
                    self._push_cascade(top, kids)
                else:
                    path = self._path() + [_label(item)]
                    self._close_all()
                    self._dispatch(path)
            elif key in ("escape", "left"):
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

        def _close_all(self) -> None:
            for dd in self._stack:
                dd.remove()
            self._stack.clear()
            self._open_top_idx = -1
            self._dd_iw = 0
            self._refresh_bar()

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
    Wsl4aiApp(args).run()
    return 0
