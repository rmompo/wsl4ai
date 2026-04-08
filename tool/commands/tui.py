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
BANNER_LABELS = [
    "",
    "WSL4AI",
    "v{version}",
    "https://github.com/rmompo/wsl4ai",
]

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

    # ── Button row (right-aligned) ────────────────────────────────────────────
    btn_chunks: list[tuple[str, str]] = []
    for i, btn in enumerate(buttons):
        cell = f" {btn} "
        sty  = _S["button_sel"] if i == btn_focus else _S["button"]
        btn_chunks.append((cell, sty))

    total_bw = sum(len(c) for c, _ in btn_chunks)
    t.append("║ ",                   style=L)
    t.append(" " * (cw - total_bw), style=T)
    for cell, sty in btn_chunks:
        t.append(cell, style=sty)
    t.append(" ║\n", style=L)

    # ── Footer ────────────────────────────────────────────────────────────────
    t.append("╚" + "═" * iw + "╝", style=L)

    return t


# ─── Data helpers for list dialogs ────────────────────────────────────────────

def _db_registry_list() -> "tuple[str, list[list[str]]]":
    """Returns (header, records) where each record is a list of display lines."""
    from commands.common import DB_PATH, connect_db
    try:
        with connect_db(DB_PATH) as con:
            rows = con.execute(
                "SELECT r.uuid, r.name, r.rel_path_host, r.rel_path_wsl, "
                "(SELECT 1 FROM uses WHERE registry_uuid = r.uuid LIMIT 1) AS in_use "
                "FROM registries r ORDER BY name COLLATE NOCASE"
            ).fetchall()
        if not rows:
            return "REGISTRY LIST", [["(no entries)"]]
        records = []
        for uuid, name, host, wsl, in_use in rows:
            records.append([
                f"UUID:   {uuid}",
                f"Name:   {name}",
                f"Host:   {host}",
                f"Wsl:    {wsl}",
                f"In Use: {'yes' if in_use else 'no'}",
            ])
        return f"REGISTRY LIST  ({len(records)} entries)", records
    except Exception as exc:
        return "REGISTRY LIST", [[f"Error: {exc}"]]


def _db_use_list() -> "tuple[str, list[list[str]]]":
    """Returns (header, records) where each record is a list of display lines."""
    from commands.common import DB_PATH, connect_db
    try:
        with connect_db(DB_PATH) as con:
            rows = con.execute(
                "SELECT w.name, r.name, u.enabled "
                "FROM uses u "
                "JOIN wsls w ON w.uuid = u.wsl_uuid "
                "JOIN registries r ON r.uuid = u.registry_uuid "
                "ORDER BY w.name COLLATE NOCASE, r.name COLLATE NOCASE"
            ).fetchall()
        if not rows:
            return "USE LIST", [["(no entries)"]]
        records = []
        for wsl, reg, enabled in rows:
            records.append([
                f"WSL:      {wsl}",
                f"Registry: {reg}",
                f"Enabled:  {'yes' if enabled else 'no'}",
            ])
        return f"USE LIST  ({len(records)} entries)", records
    except Exception as exc:
        return "USE LIST", [[f"Error: {exc}"]]


def _db_wsl_list() -> "tuple[str, list[list[str]]]":
    """Returns (header, records) where each record is a list of display lines."""
    from commands.common import DB_PATH, connect_db
    try:
        with connect_db(DB_PATH) as con:
            rows = con.execute(
                "SELECT name, user FROM wsls ORDER BY name COLLATE NOCASE"
            ).fetchall()
        if not rows:
            return "WSL LIST", [["(no entries)"]]
        records = []
        for name, user in rows:
            records.append([
                f"Name: {name}",
                f"User: {user}",
            ])
        return f"WSL LIST  ({len(records)} entries)", records
    except Exception as exc:
        return "WSL LIST", [[f"Error: {exc}"]]


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
            w = self.size.width or 80
            label_styles = [_S["text"], _S["label"], _S["text"], _S["lines"]]
            t = Text()
            t.append("\n")   # empty line above banner
            for i, (body, tent, lbl_tmpl) in enumerate(
                zip(BANNER_BODY, BANNER_TENTACLES, BANNER_LABELS)
            ):
                lbl = lbl_tmpl.replace("{version}", _APP_VERSION)
                line = Text()
                line.append(" ")                              # left padding
                line.append(body, style=_BANNER_MAGENTA)
                line.append(tent, style=_S["lines"])
                if lbl:
                    pad = (w - 1) - len(body) - len(tent) - len(lbl) - 1  # -1 left, -1 right
                    if pad > 0:
                        line.append(" " * pad)
                    line.append(lbl, style=label_styles[i])
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
            event.stop()   # prevent Textual MRO from calling this twice via subclass
            key = event.key
            n   = len(self._buttons)
            if key in ("tab", "right"):
                if self._btn_focus < n - 1:
                    self._btn_focus += 1
                    self._refresh_dlg()
            elif key in ("shift+tab", "left"):
                if self._btn_focus > 0:
                    self._btn_focus -= 1
                    self._refresh_dlg()
            elif key == "enter":
                self.dismiss(self._buttons[self._btn_focus])
            elif key == "escape":
                self.dismiss(None)

        def _refresh_dlg(self) -> None:
            try:
                self.query_one(_DialogWidget).refresh()
            except Exception:
                pass

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
            # Build flat list: (line_str, record_idx), -1 for blank separators
            self._flat: "list[tuple[str, int]]" = []
            for ri, rec in enumerate(records):
                for line in rec:
                    self._flat.append((line, ri))
                if ri < len(records) - 1:
                    self._flat.append(("", -1))  # blank separator between records
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

            # ── header line ───────────────────────────────────────────────────
            result.append([(self._header[:tw].ljust(tw), _S["label"]), (" ", "")])

            # ── separator ─────────────────────────────────────────────────────
            result.append([("─" * tw, _S["lines"]), ("─", _S["lines"])])

            # ── content window ────────────────────────────────────────────────
            window    = self._flat[self._scroll : self._scroll + content_rows]
            scrollbar = self._build_scrollbar(content_rows)

            for i, (line, ri) in enumerate(window):
                is_sel   = (ri == self._cursor and ri >= 0)
                txt      = line[:tw].ljust(tw)
                bar_char = scrollbar[i]
                if is_sel:
                    result.append([(txt, _S["item_sel"]), (bar_char, _S["lines"])])
                elif ri < 0:                   # blank separator row
                    result.append([(" " * tw, _S["text"]), (bar_char, _S["lines"])])
                else:
                    result.append([(txt, _S["text"]), (bar_char, _S["lines"])])

            # ── pad empty rows ─────────────────────────────────────────────────
            while len(result) < self._body_rows:
                result.append("")

            return result

        # ── keyboard ──────────────────────────────────────────────────────────

        def on_key(self, event: "events.Key") -> None:
            event.stop()                  # prevent Textual MRO double-dispatch
            key          = event.key
            n            = len(self._records)
            content_rows = self._body_rows - 2
            max_scroll   = max(0, len(self._flat) - content_rows)

            if key == "up":
                if self._cursor > 0:
                    self._cursor -= 1
                    self._ensure_visible(content_rows, max_scroll)
                    self._refresh_dlg()
            elif key == "down":
                if self._cursor < n - 1:
                    self._cursor += 1
                    self._ensure_visible(content_rows, max_scroll)
                    self._refresh_dlg()
            elif key == "enter":
                self.dismiss(self._buttons[self._btn_focus])
            elif key == "escape":
                self.dismiss(None)

        def _ensure_visible(self, content_rows: int, max_scroll: int) -> None:
            """Scroll so the first line of the selected record is visible."""
            first = next((i for i, (_, ri) in enumerate(self._flat) if ri == self._cursor), 0)
            if first < self._scroll:
                self._scroll = first
            elif first >= self._scroll + content_rows:
                self._scroll = min(max_scroll, first)
            self._scroll = max(0, min(self._scroll, max_scroll))

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
            action = " > ".join(path)
            if action == "Exit":
                self.exit()
                return

            # ── Theme switching ────────────────────────────────────────────────
            if len(path) >= 3 and path[0] == "Others" and path[1] == "Theme":
                theme_key = tuple(path[2:])
                theme_id  = _THEME_MAP.get(theme_key)
                if theme_id:
                    _save_theme(theme_id)
                    _load_theme()
                    self._apply_theme()
                    self.notify(f"Theme: {' › '.join(path[2:])}", timeout=2)
                else:
                    self.notify(f"Unknown theme: {theme_key}", timeout=3)
                return

            # ── List dialogs ───────────────────────────────────────────────────
            breadcrumb = " > ".join(path)

            if path == ["Registry", "List"]:
                hdr, recs = _db_registry_list()
                self.push_screen(ListDialog(breadcrumb, hdr, recs, width=80))
                return
            if path == ["Use", "List"]:
                hdr, recs = _db_use_list()
                self.push_screen(ListDialog(breadcrumb, hdr, recs))
                return
            if path == ["Wsl", "List"]:
                hdr, recs = _db_wsl_list()
                self.push_screen(ListDialog(breadcrumb, hdr, recs))
                return

            # TODO: connect remaining command handlers in the next phase
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
    global _APP_VERSION
    if not _HAS_TEXTUAL:
        print("ERROR: textual is required; run pip install -r requirements.txt")
        return 1
    _APP_VERSION = getattr(args, "app_version", "")
    _load_theme()
    Wsl4aiApp(args).run()
    return 0
