# WSL4AI TUI Specification

This document defines the interactive terminal interface for `wsl4ai tui` (Text User Interface).  
All labels, prompts, and messages in this interface must be in English.

---

## 1. Scope and command naming

- Primary command: `wsl4ai tui`
- Purpose: interactive navigation and execution of existing command/subcommand operations
- Data contract: TUI must consume the same JSON envelope model used by CLI handlers (`runtimeId`, `input`, `output`)
- Non-goal: duplicating business logic; TUI is a presentation/input layer

---

## 2. Navigation model

### 2.1 Main menu

The main menu must include, at minimum:

- `Registry`
- `Use`
- `WSL`
- `Install`
- `Whoami`
- `Start`
- `Theme`
- `Exit`

### 2.2 Submenus

Each domain opens its own submenu with available actions and a `Go back` entry.

Example for `Registry`:

- `List`
- `Add`
- `Remove`
- `Go back`

Example for `Use -> List` behavior:

- Always lists links for the current runtime WSL (default and only scope in TUI)
- `Go back`

### 2.3 Interaction keys

- Arrow keys: move selection
- Enter: select/confirm current option
- Esc: cancel current form/dialog (when applicable)

---

## 3. Input widgets by option type

TUI must choose input controls based on option semantics:

- **Typed enum option** (example: `--type ps|bash`, `--action add|remove`)
  - Use a single-choice list (no free typing)
- **Free text option** (example: names, paths, commands)
  - Use text input with validation
- **Reference option** (example: registry/wsl UUID selections)
  - Use list selection populated from query commands
  - Display human-recognizable labels plus technical id

---

## 4. Destructive action confirmations

Actions with destructive or irreversible impact must require explicit confirmation.

Minimum required confirmations:

- `registry remove`
- `use remove`
- `use disableall`
- `install database --force`
- `install alias -a remove` (recommended)

Confirmation policy:

- Show clear impact message
- Default selection must be safe (`No`)
- `Yes` required to execute
- If cancelled, operation is not executed

---

## 5. JSON/API integration rules

### 5.1 Execution flow

For any TUI action:

1. Collect user input from widgets
2. Build command/subcommand/options payload
3. Execute existing command handler/API path
4. Receive JSON envelope
5. Render via output decorator rules

### 5.1.a TUI WSL scope rule (normative)

- TUI always operates on the local runtime identity.
- TUI must not prompt for or send WSL target selector options (`--wsl-uuid`, `--wsl-name`).
- Any command needing WSL context in TUI relies on runtime-default resolution (`RuntimeIdentity`).
- TUI must not expose global-scope WSL actions such as `use list -a/--all`; that scope is CLI-only.
- `Start` in TUI is runtime-local and executes in foreground in the same terminal session (not detached).
- `install alias` in TUI must offer actions `list`, `add`, `remove`. The `--type` (shell type) option must not be exposed; shell type is always resolved from the runtime platform.
- `install update` must not appear in TUI; it is CLI-only.

### 5.1.b TUI picker model for `use` operations

For `use add`, `use remove`, `use enable`, and `use disable`, the TUI presents a **registry picker** (populated from `registry list`, filtered to registry-only rows). The WSL context is always the runtime identity; only the registry UUID is selected by the user.

- `use add`: picker shows all registries (the command will reject those already linked).
- `use enable`: picker shows all registries (command errors if no `mounted=0` link exists for the selected registry + runtime WSL).
- `use disable`: picker shows all registries (command errors if no `mounted=1` link exists).
- `use remove`: picker shows all registries (command errors if link does not exist or is `mounted=1`).
- `use disableall`: no picker; applies to all `mounted=1` links for the runtime WSL.
- `start`: picker is populated from the **use list** filtered to `mounted=1` entries for the runtime WSL.

### 5.2 Output contract

- `output.result` is always required
- `output.data` is present only for data queries (for example `list` and explicit lookup operations)
- TUI rendering must not assume `output.data` exists for write/update/delete operations

---

## 6. Rendering rules in TUI

### 6.1 Result emphasis

- Success result line uses success style (`general_ok` semantic style)
- Error result line uses error style (`general_error` semantic style)

### 6.2 Data rendering

- Query results render as readable rows/fields
- Reference pickers must show meaningful labels (name/user/path) and not only UUID
- Empty lists must show explicit empty-state message (example: `No registries found`)

---

## 7. Theme definition

TUI must use a centralized theme token map (no scattered hardcoded colors in screens).  
All color values use Rich style format: `#rrggbb` for foreground, `#rrggbb on #rrggbb` for foreground + background.  
The `fg:` questionary prefix is not valid in theme files.

### 7.0 Theme menu options

The `Theme` menu option in the TUI main menu must offer:

- `Normal (Dark)`
- `Normal (Light)`
- `Bright (Dark)`
- `Bright (Light)`
- `Color Blind (Dark)`
- `Color Blind (Light)`
- `High Contrast`

`High Contrast` is a standalone theme (no Light variant).

### 7.1 Style token reference

Each theme file defines a `styles` object with the following tokens:

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
| 9 | `text_ok` | required | — | Success message (green or equivalent) |
| 10 | `text_err` | required | — | Error message (red or equivalent) |
| 11 | `input` | required | — | Input field text |

**Auto-computation rules:**

- `item_sel` is always computed as `item + reverse` (FC becomes BC, terminal background becomes FC). It must never appear in theme files.
- `button_sel` defaults to `button + reverse`. An explicit override may be stored in the theme file when the auto-inversion is insufficient (e.g. `high_contrast`).

**Background policy:**

- TUI renders on a transparent surface — the terminal's native background is not overridden.
- Tokens that define only FC rely on the terminal background for contrast.
- The user is responsible for selecting a theme that matches their terminal (dark/light).
- `label`, `button`, and `button_sel` always carry explicit BC because they are rendered as colored blocks independent of the terminal background.

### 7.2 High Contrast exception

`high_contrast` is the only theme that must define BC on **all** tokens, including those that are FC-only in other themes.  
The required BC for all FC-only tokens is `#000000` (black).

Rationale: `high_contrast` must guarantee maximum contrast regardless of the user's terminal configuration. It cannot rely on the terminal background color being known or compatible.

Example — `lines` in other themes vs `high_contrast`:

```
normal_dark  →  "lines": "#ff7de9 bold"              (FC only, relies on terminal bg)
high_contrast → "lines": "#ffffff on #000000 bold"   (FC + BC, self-contained)
```

This rule applies to: `lines`, `item`, `text`, `text_hl`, `text_ok`, `text_err`, `input`.

### 7.3 Theme baseline mapping

Semantic alignment with existing CLI styles:

- `text_ok` → same semantic as `general_ok`
- `text_err` → same semantic as `general_error`

### 7.4 Accessibility and compatibility

- Respect `NO_COLOR` when present
- Provide non-color semantic prefixes (`OK`, `ERROR`, `WARNING`) so meaning is not color-only
- Use fallback monochrome rendering for unsupported terminals

### 7.5 Theme persistence

- Theme definitions are stored as external JSON files in `tool/tui_themes/`.
- Selected TUI theme is persisted in `conf/config.json`.
- Config schema is strict: `{ "tui": { "theme": "<theme_id>" } }`.
- The saved theme must be loaded automatically on next `wsl4ai tui` startup.
- If `config.json` is missing/invalid/unknown theme, TUI must rewrite it with default `normal_dark`.
- No backward compatibility with legacy theme-config file names or legacy key layouts.

---

## 8. English text policy

All TUI-visible strings must be English, including:

- Menu labels
- Form labels
- Validation errors
- Confirmation dialogs
- Status/result messages

No mixed-language UI text is allowed.

---

## 9. Initial screen copy (reference)

Main title:

`WSL4AI Text User Interface`

Main menu entries:

- `Registry`
- `Use`
- `WSL`
- `Install`
- `Whoami`
- `Start`
- `Theme`
- `Exit`

Shared action labels:

- `Go back`
- `Confirm`
- `Cancel`

