# WSL4AI TUI Specification

This document defines the interactive terminal interface for `wsl4ai tui` (Text User Interface).
All labels, prompts, and messages in this interface must be in English.

---

## 1. Scope and command naming

- Primary command: `wsl4ai tui`
- Purpose: interactive navigation and execution of existing command/subcommand operations
- Data contract: TUI calls `interface_*()` functions from `interface.py` (same business logic as CLI) and receives JSON envelopes
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
| Reference (registry/wsl UUID) | List selection populated from `interface_*()` query |

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
| 1 | `lines` | required | — | Box-drawing border and separator characters |
| 2 | `item` | required | — | Menu item text (not selected) |
| 3 | `item_sel` | auto | auto | Selected menu item — **never stored in theme file** |
| 4 | `label` | required | required | Section labels and headers |
| 5 | `button` | required | required | Button (not selected) |
| 6 | `button_sel` | auto/override | auto/override | Selected button |
| 7 | `text` | required | — | General body text |
| 8 | `text_hl` | required | — | Highlighted/emphasized text |
| 9 | `text_ok` | required | — | Success message |
| 10 | `text_err` | required | — | Error message |
| 11 | `input` | required | — | Input field text |

**Auto-computation:**
- `item_sel` = `item + reverse` (never in theme files)
- `button_sel` = `button + reverse` (override allowed in theme file)

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
2026-04-09 12:34:56 [interface] DEBUG  interface.interface_use_enable:599 | use enable: host=...
```

Named loggers: `TUI` (tui.py) · `interface` (interface.py).

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
  └─ Install
       ├─ Database
       └─ Alias
            ├─ List
            ├─ ─────────
            ├─ Add
            └─ Remove
  ├─ ─────────
  ├─ Log
  │    ├─ View
  │    └─ Setup
  ├─ ─────────
  └─ Theme

Exit
```
