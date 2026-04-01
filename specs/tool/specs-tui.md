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

Required semantic tokens:

- `accent` (active selection/focus)
- `success` (successful state)
- `error` (error state)
- `warning` (destructive confirmations, cautions)
- `muted` (secondary text)
- `selection` (selected menu row highlight)

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

### 7.1 Theme baseline mapping

Semantic alignment with existing CLI styles:

- `success` -> same semantic as `general_ok`
- `error` -> same semantic as `general_error`

### 7.2 Accessibility and compatibility

- Respect `NO_COLOR` when present
- Provide non-color semantic prefixes (`OK`, `ERROR`, `WARNING`) so meaning is not color-only
- Use fallback monochrome rendering for unsupported terminals

### 7.3 Theme persistence

- Theme definitions are stored as external files (JSON) in the app theme directory.
- Selected TUI theme is persisted in `config.json` next to the main script (`wsl4ai.py`).
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

