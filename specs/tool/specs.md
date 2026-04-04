# WSL4AI — specifications

This document records product and CLI rules for WSL4AI. It is part of **`specs/tool/`**, the **sole** specification tree for this package (repository root). Implementation may lag; the authoritative behavior for shipped code is still the source, but new work should follow this file unless explicitly revised.

**Layout:** **§1** runtime identity → **§2** shared core rules → **§4** command inventory (table) → **§5** command specifications in **the same order as §4** → **§6** `whoami` notes → **§7** style constants → **§8** special-command exceptions.

---

## 1. Runtime identity (`machine`, `user`)

Global contract for any code path that resolves the current host and account: CLI handlers (`args.machine`, `args.user`), future **library** entry points, and database rows that key on client identity. **All shared resolution logic must follow this section.**

**Platform assumption:** the tool targets **Linux** (e.g. Python inside WSL). Values produced on **Windows** are a **fallback** when a Linux machine-id is not available.

### 1.1 Two separate fields

- `**machine`**: opaque string identifying the **instance** (this Linux installation / WSL instance, or Windows host in fallback).
- `**user`**: effective login for the running process (typical: `getpass.getuser()`; on Linux, `pwd` may be used if stricter alignment with UID is required).

Values are stored in **distinct** columns or attributes. Uniqueness is defined on the **pair** `(machine, user)`, not on a single concatenated token.

### 1.2 Uniqueness rule

Where the schema requires one row per client identity:

- `**UNIQUE(machine, user)`** (or equivalent): the **pair** must not repeat.
- The **same** `machine` may appear with **several** different `user` values (multiple accounts on one installation).
- The **same** `user` string may appear with **different** `machine` values.
- A **duplicate** `(machine, user)` is **not** allowed.

### 1.3 Format of `machine`


| Context                | `machine` value                                                                                                                                                                    |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Linux (normal)**     | Contents of `**/etc/machine-id`** (or `/var/lib/dbus/machine-id` if adopted by implementation), **normalized** (strip; lowercase hex). **No** prefix — this is the canonical case. |
| **Windows (fallback)** | `**win:`** plus a stable host token, e.g. `win:DESKTOP-HOST1` from `COMPUTERNAME` (or equivalent), **normalized** as documented in code.                                           |


Only **Windows fallback** uses the `**win:`** prefix so it is never confused with a bare Linux machine-id.

### 1.4 Examples

```text
machine                                    user
-----------------------------------------  -----
win:DESKTOP-HOST1                          alice
win:DESKTOP-HOST1                          bob
win:DESKTOP-HOST12                         alice
dcbb4f2e3e5f4a1b9c8d7e6f5a4b3c2d           bob
```

The fourth row is a normalized Linux instance id; the first three are Windows fallback.

### 1.5 Library and CLI

Any **library** API that exposes runtime identity must return `**machine`** and `**user**` consistent with §1.1–§1.3 so that persistence, `use` workflows, and CLI behavior agree.

### 1.6 `RuntimeIdentity` (extended CLI context)

Handlers may receive `**args.runtime_identity**` (`RuntimeIdentity` in `commands/common.py`): `**machine**`, `**user**`, and `**wsl_name**` (typically `WSL_DISTRO_NAME` or `**default**`). Used to resolve or create `**wsls**` rows when `**--wsl-uuid**` / `**--wsl-name**` are omitted. `**whoami**` still prints only `**machine**` and `**user**`.

---

## 2. Rules for core (non-special) commands

Shared rules for any handler that is **not** listed in **§8** as exempt. Per-command behavior and links to standalone spec files are in **§5** (and **§6** for `whoami`).

### 2.1 Database: existence and availability

Before performing work that assumes a working catalog:

1. The database file must **exist** (e.g. `ddbb/wsl4ai.db`).
2. The database must be **usable**: it must be possible to open it (same connection settings as normal use: WAL, `foreign_keys`, timeouts) and run a minimal sanity check (e.g. a simple query / expected tables).

If the check fails: print an error (see §2.4 for styling), return exit code ≠ 0 (see §2.2).

Prefer a **single shared helper** used by all core handlers so behavior stays consistent.

### 2.1.a Runtime default for optional WSL selectors (normative)

For any command/subcommand that exposes WSL target options (`--wsl-uuid` / `--wsl-name`):

- Both options are optional unless the command-specific spec says otherwise.
- If neither option is provided, the effective target WSL is resolved from `RuntimeIdentity` (runtime `wsl_name` + runtime `user`, then resolved `wsl_uuid`).
- This runtime-default rule is global and applies across all command specs that expose optional WSL selectors.

### 2.2 Exit codes


| Outcome                                                                   | Exit code                    |
| ------------------------------------------------------------------------- | ---------------------------- |
| Operation completed successfully                                          | `0`                          |
| Any failure (missing/unusable DB, validation, not found, SQL error, etc.) | Non-zero — **typically `1`** |


**Placeholders** (commands registered but not implemented): should return a non-zero exit code if their outcome is not a real success, once policy is aligned with “only 0 means OK”.

### 2.3 JSON envelope (single contract for request and response)

All commands and subcommands must produce their outcome as a single JSON document on stdout (no human-formatted output is required). The same top-level structure is used for *input* and *output* so that:

- A future “API mode” can accept JSON requests directly.
- The CLI and the interactive TUI can call the same CRUD logic and only *format* what they want to display.

#### 2.3.1 Top-level shape

```json
{
  "runtimeId": {
    "machine": "",
    "user": ""
  },
  "input": {
    "command": "",
    "subcommand": "",
    "options": [
      { "key": "", "value": "" }
    ]
  },
  "output": {
    "result": {
      "status": 0,
      "message": "",
      "uuid": ""
    },
    "data": {
      "rows": [
        {
          "fields": [
            { "key": "", "value": "" }
          ]
        }
      ]
    }
  }
}
```

#### 2.3.2 Field rules (normative)

- `**runtimeId.machine**`: the resolved runtime machine identifier per **§1.3**.
- `**runtimeId.user`**: the resolved runtime user identifier per **§1.1**.
- `**input.command`**: top-level command name (e.g. `registry`, `use`, `wsl`, `install`).
- `**input.subcommand**`: nested subcommand name when applicable (e.g. `add`, `list`, `remove`, `set`); empty string if the command has no nested subcommand.
- `**input.options**`:
  - Each entry is a key/value pair corresponding to a CLI option that was set or passed.
  - `**key**` should use the long option form (e.g. `--registry-name`) even if the user typed a short form.
  - `**value**` is a string representation (for flags, use `"true"`/`"false"` when included).
- `**output.result.status**`: exit code for the operation (matches **§2.2**).
- `**output.result.message`**: short human-readable summary of the outcome.
- `**output.result.uuid**`:
  - Optional; set only when the command’s primary output is a newly created UUID (e.g. insert operations).
  - Otherwise omit or use an empty string.
- `**output.data.rows**`:
  - List of records. Empty list means “no records” (still success if appropriate).
- `**output.data.rows[].fields**`:
  - List of `{key,value}` pairs for that record.
  - Keys are command-specific but must be stable and documented in the command’s spec section(s).

#### 2.3.3 Example (shape only)

```json
{
  "runtimeId": {
    "machine": "dcbb4f2e3e5f4a1b9c8d7e6f5a4b3c2d",
    "user": "alice"
  },
  "input": {
    "command": "registry",
    "subcommand": "add",
    "options": [
      { "key": "--name", "value": "myproj" },
      { "key": "--host", "value": "projects/foo" },
      { "key": "--wsl", "value": "work/foo" }
    ]
  },
  "output": {
    "result": {
      "status": 0,
      "message": "registry added",
      "uuid": "550e8400-e29b-41d4-a716-446655440000"
    },
    "data": {
      "rows": [
        {
          "fields": [
            { "key": "registryUuid", "value": "550e8400-e29b-41d4-a716-446655440000" },
            { "key": "registryName", "value": "myproj" }
          ]
        }
      ]
    }
  }
}
```

### 2.4 Terminal output — `GENERAL_OK` and `GENERAL_ERROR` (legacy human formatting)

For core commands, user-visible **result** lines should reflect success vs failure using the semantic styles in `commands/style_constants.py`:

- **Success** → wrap message with `tty_styled(..., GENERAL_OK)` (green background, white text in TTY).
- **Failure** → wrap message with `tty_styled(..., GENERAL_ERROR)` (red background, white text in TTY).

`tty_styled` must respect `NO_COLOR` and non-TTY stdout (no escape codes when inappropriate).

**Exception:** `**registry list`** uses `**LIST_IN_USE` / `LIST_NOT_IN_USE**` on the registry **title** line only (see **§5.1**), not the generic OK/ERROR pair for that line.

---

## 4. Command inventory

**Operational order (recommended):** **registry add** → **use add** → **use enable**; to tear down: **use disable** → **use remove** → **registry remove** (only when no `**uses`** remain). `**wsl set**` can set `**wsls.cli_command**` after a `**wsls**` row exists.


| Command                    | Shortcut | Purpose                                                                                                   |
| -------------------------- | -------- | --------------------------------------------------------------------------------------------------------- |
| `wsl4ai install tool`      | `it`     | Install/verify WSL4AI tool layout (no options).                                                           |
| `wsl4ai install database`  | `id`     | Create the database if missing; with `-f/--force`, overwrite (destructive reset).                         |
| `wsl4ai install alias`     | `ia`     | Add/remove one or more shell aliases in PowerShell or Bash (`-a/-t/-n` required).                         |
| `wsl4ai install update`    | `iu`     | Check for and apply a new version of the tool. `--check` flag prints available version without updating.  |
| `wsl4ai registry list`     | `rl`     | List `registries` rows with resolved paths and linked `wsls` lines (`uses.mounted` on link lines).        |
| `wsl4ai registry add …`    | `ra`     | Insert a row into `registries` (mount definition).                                                        |
| `wsl4ai registry remove …` | `rr`     | Delete a row from `registries` **only if** there are **no** rows in `uses` for that registry.             |
| `wsl4ai use list`          | `ul`     | List `uses` links (default: runtime WSL; filter by WSL or use `-a/--all` for global list).               |
| `wsl4ai use add …`         | `ua`     | Link `wsls` + `registries` in `uses` (`mounted=0`); create `wsls` if needed (`cli_command` NULL).         |
| `wsl4ai use remove …`      | `ur`     | Remove a `uses` row if `mounted=0`.                                                                       |
| `wsl4ai use enable …`      | `ue`     | Bind-mount host path onto existing WSL directory; then set `uses.mounted = 1`.                            |
| `wsl4ai use disable …`     | `ud`     | Unmount WSL directory (directory preserved for future `enable`); then set `uses.mounted = 0`.             |
| `wsl4ai use disableall`    | `uda`    | Unmount all `mounted=1` uses of the runtime WSL; update DB. Supports `-q/--quiet`.                       |
| `wsl4ai wsl list`          | `wl`     | List all known `wsls` rows and their `cli_command` values.                                                |
| `wsl4ai wsl set …`         | `ws`     | Set `wsls.cli_command` (row must exist).                                                                  |
| `wsl4ai whoami`            | `wai`    | Print the current `machine` and `user` runtime identity.                                                  |
| `wsl4ai tui`               | -        | Open the interactive text user interface.                                                                 |
| `wsl4ai start`             | -        | Run one mounted use in foreground: cd to resolved WSL path and execute that WSL `cli_command`.           |

The SQLite model uses `**registries**`, `**wsls**`, and `**uses**` (`mounted` only; no `enabled` column). Path bases (`HOST_PROJECTS`, `WSL_PROJECTS`) are read directly from **`conf/local.env`** (never from the database); there is no `parameters` table.

---

## 5. Command specifications

This section is an index only. Operational details must live in grouped files named `specs-[command].md`.

### 5.1 Grouped command specification files

- `install` -> [`specs-install.md`](specs-install.md)
- `registry` -> [`specs-registry.md`](specs-registry.md)
- `use` -> [`specs-use.md`](specs-use.md)
- `wsl` -> [`specs-wsl.md`](specs-wsl.md)
- `whoami` -> [`specs-whoami.md`](specs-whoami.md)
- `start` -> [`specs-start.md`](specs-start.md)
- `tui` (interactive mode spec) -> [`specs-tui.md`](specs-tui.md)
- `-v/--version` flag -> [`specs-version.md`](specs-version.md)

### 5.2 Grouping rule (normative)

- Per-command and per-subcommand behavior must be documented in the corresponding grouped file.
- `specs.md` should only keep global contracts (runtime identity, JSON envelope, style semantics, inventory).
- Any command-specific details discovered here must be moved to the corresponding grouped file.

### 5.3 TUI config location (global reference)

- `wsl4ai tui` persists user-selected theme in `conf/config.json`.
- Theme key path: `tui.theme`.
- If config is missing/invalid/unknown, implementation must recreate it with default `normal_dark`.
- TUI command flows are runtime-local: they must not send WSL target selector options and rely on runtime identity defaults.
- TUI must not expose global WSL scope actions (including `use list -a/--all`); global scope remains CLI-only.

---

## 6. Command-specific location

`whoami` details are defined in [`specs-whoami.md`](specs-whoami.md), not in this index file.

---

## 7. Style constants (reference)

Defined in `commands/style_constants.py`:


| Constant                            | Role                                                  |
| ----------------------------------- | ----------------------------------------------------- |
| `LIST_IN_USE`                       | `registry list` title when registry is linked (busy). |
| `LIST_NOT_IN_USE`                   | `registry list` title when registry is not linked.    |
| `GENERAL_OK`                        | Core command success messages.                        |
| `GENERAL_ERROR`                     | Core command error messages.                          |
| `tty_styled(text, style, stream=…)` | Apply style when TTY and `NO_COLOR` unset.            |
| `HELP_SECTION`                      | Help section headers (`Usage:`, `commands:`, `subcommands:`, `Optional:`). Bold yellow. Defined in `commands/cli_help.py`. |
| `HELP_NAME`                         | Help option/command/subcommand names. Bold cyan. Defined in `commands/cli_help.py`. |


**Colors:** standard ANSI SGR only — **bright white** foreground (`97`) **before** **red** (`41`) or **green** (`42`) background in the same sequence (e.g. `\x1b[97;42m`), so Windows consoles that mishandle `42;97` still show white on green.

---

## 8. CLI help and error formatting

Implemented in `commands/cli_help.py`. Applies to all parsers (`Wsl4aiArgumentParser` + `Wsl4aiHelpFormatter`).

### 8.1 Usage label

- All `Usage:` labels (in `-h` output and error output) are **capitalized** and colored with `HELP_SECTION` (bold yellow).
- Applies to root help, router help, and leaf command help.

### 8.2 Section headings

Section headings (`commands:`, `subcommands:`, `Optional:`, `Required:`) are normalized and colored with `HELP_SECTION`.

### 8.3 Option/command names

Option flags and command/subcommand names in help listings are colored with `HELP_NAME` (bold cyan), with ANSI overhead compensated in column alignment.

### 8.4 Error output

On parse error (unknown command, missing required option, etc.), the parser prints a **minimal usage line only** — no list of choices:

| Context | Error output |
| ------- | ------------ |
| Root parser | `Usage: wsl4ai [-h] <command> [<subcommand>] [options]` |
| Router subparser | `Usage: wsl4ai <command> [-h] <subcommand> [options]` |
| Leaf subparser | `Usage: wsl4ai <command> <subcommand> [-h] [options]` |

All output to `stderr`; exit code `2`.

### 8.5 Footer

Root `-h` shows one footer line: `Per-command help: wsl4ai <command> --help`.  
Router `-h` shows: `Per-subcommand help: wsl4ai <command> <subcommand> --help`.  
No redundant "Per-command options" line.

---

## 9. Special commands — explicit non-application of §2

`install` (including `install tool`, `install database`, `install alias`, `install update`) is **not** bound by §2 unless a bullet is added here for a specific case.