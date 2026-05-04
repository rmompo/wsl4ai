# WSL4AI TUI Specification

This document defines the interactive terminal interface for `wsl4ai tui` (Text User Interface).
All labels, prompts, and messages in this interface must be in English.

---

## 1. Scope and command naming

- Primary command: `wsl4ai tui`
- Purpose: interactive navigation and execution of existing command/subcommand operations
- Data contract: TUI calls `api_*()` functions from `api.py` (same business logic as CLI) and receives JSON envelopes
- Non-goal: duplicating business logic; TUI is a presentation/input layer
- Architecture reference: [`specs-architecture.md`](specs-architecture.md)

---

## 2. Navigation model

### 2.1 Main menu

```
Registry | Use | Wsl | Start | Others | Exit
```

| Entry | Submenu |
|-------|---------|
| `Registry` | List · Add · Remove |
| `Use` | List · Add · Remove · Enable · Disable |
| `Wsl` | List · Set |
| `Start` | *(direct action — shows mounted-use picker)* |
| `Others` | Install › Database · Alias (List · Add · Remove) · Theme |
| `Exit` | *(exits TUI)* |

### 2.2 Interaction keys

- Arrow keys / Tab: move selection
- Enter: select/confirm
- Escape: cancel current dialog or close dropdown

---

## 3. Input widgets by option type

| Option type | Widget |
|-------------|--------|
| Typed enum (`add|remove|list`) | Single-choice list |
| Free text (names, paths, commands) | Text input with validation |
| Reference (registry/wsl UUID) | List selection populated from `api_*()` query |

---

## 4. Destructive action confirmations

Actions with destructive or irreversible impact require explicit confirmation via `ConfirmDialog`:

| Action | Dialog prompt |
|--------|--------------|
| `registry remove` | "Remove '\<name\>'?" |
| `use remove` | "Remove use for '\<name\>'?" |
| `use enable` | "Enable use for '\<name\>'?" |
| `use disable` | "Disable use for '\<name\>'?" |
| `install database` | "Create database?" |
| `install alias remove` | "Remove alias '\<name\>'?" |

Default selection is always safe (`Cancel`). `Ok` required to execute.

---

## 5. TUI scope rules (normative)

### 5.1 Runtime identity only

- TUI always operates on the local runtime identity (`RuntimeIdentity`).
- TUI does not prompt for or send WSL target selector options (`--wsl-uuid`, `--wsl-name`).
- `use list -a/--all` (global scope) is CLI-only and not exposed in TUI.

### 5.2 Command availability

| Command | TUI | CLI |
|---------|-----|-----|
| `registry list/add/remove` | ✓ | ✓ |
| `use list/add/remove/enable/disable` | ✓ | ✓ |
| `use disableall` | — | ✓ |
| `wsl list/set` | ✓ | ✓ |
| `install database` | ✓ | ✓ |
| `install alias list/add/remove` | ✓ | ✓ |
| `install update` | — | ✓ |
| `whoami` | — | ✓ |
| `start` | ✓ (picker) | ✓ (by name/uuid) |
| `theme` | ✓ (TUI-only) | — |

### 5.3 Start behavior

- TUI **Start** shows a picker of all `mounted=1` uses for the runtime WSL.
- After the user selects and confirms, the TUI exits and `cmd_tui` runs the tool in foreground.
- When the tool exits, `cmd_tui` relaunches the TUI automatically (loop).
- The loop only exits when the user quits the TUI without selecting Start.

### 5.4 Use pickers

| Action | Picker content |
|--------|---------------|
| `use add` | Registries not yet linked to runtime WSL |
| `use remove` | All use links for runtime WSL |
| `use enable` | Use links with `mounted=0` for runtime WSL |
| `use disable` | Use links with `mounted=1` for runtime WSL |

---

## 6. Rendering rules

### 6.1 Result emphasis

- Success notifications use `timeout=3`.
- Error notifications use `_notify_err()` which logs to the log file **and** shows a Textual notification (`timeout=4` or `5` for critical).

### 6.2 Data rendering

- Query results render as selectable rows in `ListDialog`.
- Reference pickers show meaningful labels (name, path) alongside UUIDs.
- Empty lists show explicit empty-state message (e.g. `No registries found`).

---

## 7. Theme definition

TUI uses a centralized theme token map in `tool/tui_themes/*.json`. No hardcoded colors in screens.
All color values use Rich style format: `#rrggbb` or `#rrggbb on #rrggbb`.

### 7.0 Theme menu options

Available in `Others › Theme` via `ThemeDialog` (live preview on navigation):

| Display name | Theme ID |
|---|---|
| Dark › Normal | `normal_dark` |
| Dark › Bright | `bright_dark` |
| Dark › Color Blind | `color_blind_dark` |
| Light › Normal | `normal_light` |
| Light › Bright | `bright_light` |
| Light › Color Blind | `color_blind_light` |
| High Contrast | `high_contrast` |

### 7.1 Style token reference

| # | Token | FC | BC | Description |
|---|---|---|---|---|
| 1 | `lines` | required | — | Box-drawing borders, separators, scrollbar characters, punctuation |
| 2 | `item` | required | — | Inactive menu item text |
| 3 | `item_sel` | auto | auto | Active/focused menu item — **never stored in theme file** |
| 4 | `label` | required | required | Section headers, breadcrumbs, list header row, info lines |
| 5 | `button` | required | required | Navigation hint boxes in button row |
| 6 | `button_default` | required | required | Action button confirmed by Enter (Ok, Add, Remove, Save, Set…) |
| 7 | `button_cancel` | required | required | Cancel button dismissed by Esc |
| 8 | `button_both` | required | required | Close button dismissed by Esc or Enter |
| 9 | `text` | required | — | Body text in dialogs, field values |
| 10 | `text_hl` | required | — | Emphasized text, field labels |
| 11 | `text_ok` | required | — | Success result text |
| 12 | `text_err` | required | — | Error result text |
| 13 | `input` | required | — | Inactive input field text |
| 14 | `input_sel` | auto/override | auto/override | Active (focused) input field |

**Auto-computation:**
- `item_sel` = `item + reverse` (never in theme files)
- `input_sel` = `input + reverse` (override allowed in theme file)

### 7.2 High Contrast exception

`high_contrast` must define BC on **all** tokens (including FC-only tokens in other themes). Required BC: `#000000`.

### 7.3 Theme persistence

- Theme definitions: `tool/tui_themes/<theme_id>.json`
- Selected theme persisted in `conf/config.json` at `tui.theme`
- Default: `normal_dark` (written on first run or if config is missing/invalid)

---

## 8. Log configuration

TUI logging is configured via `conf/config.json` under the `log` key:

```json
{
  "tui": { "theme": "normal_dark" },
  "log": {
    "level": "WARNING",
    "file":  "logs/wsl4ai.log"
  }
}
```

| Key | Values | Default | Notes |
|-----|--------|---------|-------|
| `log.level` | `DEBUG` · `INFO` · `WARNING` · `ERROR` · `NONE` | `WARNING` | `NONE` disables all logging |
| `log.file` | filename or relative path | `logs/wsl4ai.log` | Relative to `tool/`; absolute paths used as-is; `~` and `$HOME` expanded; directory created automatically |

Log format:
```
2026-04-09 12:34:56 [TUI] ERROR  tui._confirm_toggle:1345 | mount failed: ...
2026-04-09 12:34:56 [interface] DEBUG  interface.api_use_enable:599 | use enable: host=...
```

Named loggers: `TUI` (tui.py) · `interface` (api.py).

### 8.1 Log viewer (`Others › Log › View`)

- Opens `LogViewDialog`: shows last N lines of the log file, **newest at top**.
- Auto-refreshes every 2 seconds. Displays up to 500 lines, 35 visible at a time (width 160).
- Scroll with Up/Down (Up=older, Down=newer), Home/End for extremes.
- Lines are color-coded by level keyword in the line text.
- Escape or Enter closes the viewer.

### 8.2 Log level selector (`Others › Log › Setup`)

- Opens `LogSetupDialog`: a list picker of `DEBUG · INFO · WARNING · ERROR · NONE`.
- Current level (from `conf/config.json`) is pre-selected.
- Enter confirms the selection; Escape cancels.
- On confirm: writes new level to `conf/config.json` and updates all running loggers immediately (no restart needed).
- `NONE` disables all logging output.

---

## 9. English text policy

All TUI-visible strings must be English: menu labels, form labels, validation errors, confirmation dialogs, status/result messages.

---

## 10. Menu reference

```
Registry
  ├─ List
  ├─ ─────────
  ├─ Add
  └─ Remove

Use
  ├─ List
  ├─ ─────────
  ├─ Add
  ├─ Remove
  ├─ ─────────
  ├─ Enable
  └─ Disable

Wsl
  ├─ List
  ├─ ─────────
  └─ Set

Start  (direct — mounted-use picker)

Others
  ├─ Log
  │    ├─ View
  │    └─ Setup
  ├─ ─────────
  ├─ Theme
  ├─ ─────────
  └─ Install
       ├─ Database
       └─ Alias
            ├─ List
            ├─ ─────────
            ├─ Add
            └─ Remove

Exit
```

---

## 11. Banner

The banner occupies the full terminal width (Textual `1fr`) and is **5 rows tall** (1 blank padding row + 4 content rows). It is rendered as a single Rich Text block.

### 11.1 Layout

```
                                               WSL4AI  v1.5.x
 ▄███▄                          https://github.com/rmompo/wsl4ai
 █▀◉◉▀█▃▄▂▂▁
 ▀█▄▄█▀▄▃▄▂▃▂▂▁                           user@wsl-name(machine)
```

| Row | Left section | Right section |
|-----|-------------|---------------|
| 0 | *(blank padding)* | — |
| 1 | ` ` + body[0] (magenta) | right-aligned: ` WSL4AI ` (label) + ` ` + `v{version}` (text) |
| 2 | ` ` + body[1] (magenta) | right-aligned: GitHub URL (lines) |
| 3 | ` ` + body[2] (magenta) + tentacles[2] (lines) | *(blank)* |
| 4 | ` ` + body[3] (magenta) + tentacles[3] (lines) | right-aligned: identity string (see below) |

### 11.2 Octopus art

The octopus body is always rendered in fixed bright magenta (`#ff00ff`), regardless of theme. Tentacles use the `lines` style token.

```
BANNER_BODY      = ["▄███▄", "█▀◉◉▀█", "▀█▄▄█▀", "▄▀▄▄▄▀"]
BANNER_TENTACLES = ["",      "",       "▃▄▂▂▁",  "▄▃▄▂▃▂▂▁"]
```

### 11.3 Right-aligned information

| Row | Content | Style token |
|-----|---------|-------------|
| 1 | ` WSL4AI ` | `label` |
| 1 | `v{version}` | `text` |
| 2 | `https://github.com/rmompo/wsl4ai` | `lines` |
| 4 | `{user}` | `text_hl` |
| 4 | `@` | `lines` |
| 4 | `{wsl_name}` | `text_hl` |
| 4 | `(` `)` | `lines` |
| 4 | `{machine}` | `text_hl` |

All right-aligned content is padded dynamically to terminal width.

---

## 12. Menu bar and navigation

### 12.1 Horizontal bar layout

The menu bar (`MenuBar` widget) is **3 rows tall** and spans the full terminal width.

```
────────────────┬────────┬──────────────────────────────────────
  Registry  Use  │ Others │  Wsl  Start  Exit
────────────────┴┌───────┘──────────────────────────────────────
```

**Row 1 — top border:** full-width `─` line. `┬` characters mark the left and right sides of the `Others` box.

**Row 2 — labels:** 2-cell left margin; items placed left to right with fixed gaps.
- Normal item — unfocused: plain label in `item` style. Focused or dropdown open: ` label ` in `item_sel` style (1-cell padding each side).
- `Others` item: always enclosed in `│ Others │` (borders in `lines`). Focused/open: label in `item_sel`; otherwise: label in `item`.
- Gap between consecutive normal items: 2 cells. Gap at `Others` boundary: 1 cell.

**Row 3 — bottom border:** full-width `─` line.
- `┴` characters close the `Others` box connectors.
- When a dropdown is open: `┌...┐` drawn at the dropdown attachment point.

### 12.2 Vertical dropdown menus

First-level dropdowns attach below row 3 of the menu bar (no top border — bar row 3 provides it with `┌...┐`). Cascading submenus open to the right of the parent item and include their own top border.

**First-level dropdown body:**
```
│ Item                    │
├─────────────────────────┤   ← separator  (None entries in MENU list)
│ Sub-item               »│   ← item with children
└─────────────────────────┘
```

**Cascading submenu:**
```
┌──────────┐
│ Child 1  │
├──────────┤
│ Child 2  │
└──────────┘
```

- Inner width: widest label in the list + 2 (padding), minimum 6.
- Items with children: label padded to `iw-2` + ` »`.
- Separators: `├──┤` (not selectable, skipped by cursor).
- Active item: `item_sel` style. Inactive: `item` style. Borders and separators: `lines` style.

### 12.3 Keyboard navigation

| Key | Scope | Action |
|-----|-------|--------|
| `←` / `→` | Bar | Move between top-level items |
| `↑` / `↓` | Dropdown | Move cursor between selectable items, skip separators |
| `Enter` | Bar | Open dropdown for item with submenu; trigger action for leaf |
| `Enter` | Dropdown | Open cascade for item with children; trigger action for leaf |
| `Escape` | Dropdown | Close current level; return to bar or parent menu |

---

## 13. Dialog frame design

All modal dialogs share a common frame rendered by `_render_dialog()`. The frame is centered on screen (Textual `align: center middle`).

### 13.1 Frame structure

```
╔╣ Breadcrumb › Path ╠════════════════╗   ← header
║                                     ║   ← blank row
║  body content line 1                ║   ← body_rows rows
║  body content line 2                ║     cw = width - 4
╠═════════════════════════════════════╣   ← separator
║  ↑↓ move   Home newest    Cancel Ok ║   ← button row
╚═════════════════════════════════════╝   ← footer
```

**Dimensions:**
- `iw` (inner width) = `width - 2` — space between `║` borders
- `cw` (content width) = `width - 4` — content area (1-space margin each side)
- Total height = `body_rows + 5` (header + blank + body_rows + separator + button_row + footer)

**Header:** `╔╣ breadcrumb ╠═══╗` — breadcrumb in `label` style; `╔╣`, `╠`, `═`, `╗` in `lines` style.

**Body:** each line is `║ content ║`. Content can be:
- A plain string: rendered in `text` style, padded to `cw`.
- A list of `(chunk, style)` pairs: each chunk rendered with its own style; total padded to `cw`.

**Separator:** `╠═══╣` in `lines` style.

**Footer:** `╚═══╝` in `lines` style.

### 13.2 List area (ListDialog)

Dialogs that display record lists (`ListDialog` and subclasses) use a structured body:

```
║  List header  (3/5 entries)               ║  ← header (label, full cw, no scrollbar)
║  ──────────────────────────────────────── ║  ← separator (lines, full cw, no scrollbar)
║  Field label   field value             ▓  ║  ← content row (tw = cw-2, scrollbar at right)
║  Field label   field value             ▓  ║
║                                        ▓  ║  ← blank row between records
║  Field label   field value             ░  ║
║                                        ░  ║  ← padding rows (fill to content_rows)
```

**Header row:** `{header_label}  ({cursor+1}/{n} entries)` — `label` style; occupies full `cw`; no scrollbar column.

**Separator row:** `─` × `cw` — `lines` style; occupies full `cw`; no scrollbar column.

**Content rows:** text width `tw = cw - 2` (leaves room for 1-col separator + 1 scrollbar column).
- Non-selected record: label part in `text_hl`, value part in `text`.
- Selected record: entire row in `item_sel`.
- Blank row between records: empty in `text`.
- 1-col separator (` `) in `lines` style between text and scrollbar.

**Scrollbar:** occupies the rightmost column of content rows only (does NOT extend over header or separator rows).
- `▓` — thumb (visible region)
- `░` — track (non-visible region)
- When all records fit: entire bar is `▓`.
- Proportional thumb height: `max(1, round(rows² / total))`, clamped to `[1, rows]`.

**Navigation keys in list dialogs:**

| Key | Action |
|-----|--------|
| `↑` | Move cursor to previous record; scroll if needed |
| `↓` | Move cursor to next record; scroll if needed |
| `Enter` | Confirm selection or open action |
| `Escape` | Dismiss dialog |

Nav hint `↑↓ move` appears left-aligned in the button row.

### 13.3 Button row

The button row is always the last content row before the footer.

**Layout:** nav hints left-aligned + elastic gap + action buttons right-aligned, all within `cw`:

```
║  ↑↓ move  Home newest  PgUp/PgDn page         Cancel Ok ║
  ←──── nav hints (button style) ─────────────────────────→
                                            ←─ buttons ──→
```

- Each hint: ` hint text ` with `button` style.
- Hints separated by single spaces.
- Gap between hints and buttons: `max(1, cw - left_w - right_w)` spaces.
- Action buttons separated by single spaces.
- All buttons centered to the width of the widest button label.

### 13.4 Button types and semantics

Button style is derived automatically from the button label. There is no focus state or navigation between buttons.

| Label | Style token | Trigger key | Typical position |
|-------|------------|-------------|-----------------|
| `Cancel` | `button_cancel` | `Escape` | Left of default action |
| `Close` | `button_both` | `Escape` or `Enter` | Rightmost (sole button) |
| Other (`Ok`, `Add`, `Remove`, `Save`, `Set`…) | `button_default` | `Enter` | Rightmost |

**Positioning rule:** `Cancel` is always to the left of the default action button. `Close` appears alone. Default action buttons are always rightmost.

**Color semantics** (values are theme-defined, not hardcoded):
- `button_default` — affirmative/confirmative color (green in dark themes, blue in color-blind themes)
- `button_cancel` — destructive/dismissive color (red in dark themes, orange in color-blind themes)
- `button_both` — neutral color (amber/yellow in dark themes)
- `button` — muted color for nav hints (grey in all themes)

---

## 14. Visual style tokens

Style tokens are **semantic identifiers** that connect the rendering code to color/formatting values defined in theme files. They must not be confused with themes (which supply the actual color values).

The complete token set and their rendering roles:

| Token | Used in | Role |
|-------|---------|------|
| `lines` | All frames, menus, scrollbar | Box-drawing (`╔`, `║`, `─`, `│`, `┌`, `└`…), scrollbar (`▓`, `░`), punctuation |
| `item` | Menu bar, dropdowns | Inactive menu item text |
| `item_sel` | Menu bar, dropdowns, list rows | Active/highlighted item — **auto-computed** as `item + reverse`; never in theme files |
| `label` | Dialog header, list header, info lines | Section titles, breadcrumbs, status/info text |
| `button` | Button row | Navigation hint boxes |
| `button_default` | Button row | Affirmative action button (Enter trigger) |
| `button_cancel` | Button row | Cancel button (Esc trigger) |
| `button_both` | Button row | Close button (Esc or Enter trigger) |
| `text` | Dialog body | General body text, field values |
| `text_hl` | Dialog body, form fields | Emphasized text, field label columns |
| `text_ok` | Notifications | Success result messages |
| `text_err` | Notifications, log viewer | Error result messages |
| `input` | Form fields | Inactive (unfocused) input field |
| `input_sel` | Form fields | Active (focused) input field — auto-computed from `input`; override allowed in theme file |

**Key invariants:**
- `item_sel` is **never** stored in theme files — always auto-computed as `item + reverse`.
- `input_sel` may be overridden per-theme; defaults to `input + reverse`.
- Button appearance depends solely on the button's semantic name — no focus state.
- The `High Contrast` theme must define `BC` on **all** tokens. Required BC: `#000000`.
