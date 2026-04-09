# Specification: `wsl4ai install ...`

Command group for setup and shell integration tasks.

---

## 1. Subcommands

| Subcommand | Shortcut | Purpose |
|------------|----------|---------|
| `install database` | `id` | Create the database if missing; `--force` for destructive reset |
| `install alias` | `ia` | Add/remove/list shell aliases in Bash or PowerShell profile |
| `install update` | `iu` | Check for and apply a new version of the tool from GitHub |

> **Note:** `install tool` and its shortcut `it` have been removed. Layout validation is no longer a standalone command.

---

## 2. `install database`

- Purpose: initialize database or reset it.
- Options: optional `-f/--force` for destructive overwrite.
- Output contract: always `output.result`.

```mermaid
flowchart LR
    subgraph CLI
        id["wsl4ai install database\nwsl4ai id [-f]"]
        cmd["install_database.cmd_install_database()"]
        id --> cmd
    end
    subgraph Interface["interface.py"]
        iface["interface_install_database(force)"]
    end
    subgraph TUI
        dispatch["_dispatch\n(['Others','Install','Database'])"]
        confirm["ConfirmDialog\n→ _do_install_db()"]
        dispatch --> confirm
    end

    cmd --> iface
    confirm --> iface
    iface -->|"envelope"| cmd
    iface -->|"envelope → status"| confirm
    cmd -->|"emit_from_interface()"| stdout([stdout])
    confirm -->|"notify success/error"| ui([TUI notify])
```

---

## 3. `install alias`

- Purpose: add/remove/list aliases in shell profile targets.
- Target file: `~/.startup-wsl4ai.sh` (Linux) or PowerShell profile (Windows); auto-detected from OS — no `--type` option.
- Required options:
  - `-a/--action` → `add|remove|list`
  - `-n/--name` → repeatable alias names (required only for `add` and `remove`)
- Validation rules:
  - `add`: existing alias → error
  - `remove`: missing alias → error
  - `list`: no `--name` required; returns all aliases in the managed block
- Aliases are managed inside the markers block:
  ```
  # >>> WSL4AI BEGIN >>>
  ...
  # <<< WSL4AI END <<<
  ```
- Output contract: always `output.result`; `list` action includes `output.data.rows`.

```mermaid
flowchart LR
    subgraph CLI
        ia["wsl4ai install alias\nwsl4ai ia -a list|add|remove [-n name]"]
        cmd["install_alias.cmd_install_alias()"]
        ia --> cmd
    end
    subgraph Interface["interface.py"]
        iface_list["interface_alias_list()"]
        iface_add["interface_alias_add(names)"]
        iface_rm["interface_alias_remove(names)"]
    end
    subgraph TUI
        alist["AliasListDialog.__init__()"]
        aadd["AliasAddDialog._try_submit()"]
        arm_init["AliasRemoveDialog.__init__()"]
        arm_do["AliasRemoveDialog._confirm_remove()"]
        arm_init --> arm_do
    end
    subgraph TUI_Dec["tui_decorator.py"]
        rec["alias_list_records()"]
    end

    cmd --> iface_list
    cmd --> iface_add
    cmd --> iface_rm
    alist --> iface_list --> rec --> alist
    arm_init --> iface_list --> rec
    aadd --> iface_add
    arm_do --> iface_rm
    iface_list -->|"envelope"| cmd
    cmd -->|"emit_from_interface()"| stdout([stdout])
    aadd -->|"notify success/error"| ui([TUI notify])
    arm_do -->|"notify success/error"| ui
```

---

## 4. `install update`

- Purpose: check for and apply a new version of the tool from GitHub.
- Options: optional `--check` — print available version without applying the update.
- Behavior:
  1. Delegates immediately to `conf/wsl4ai-update.py` via `os.execv`.
  2. The updater downloads `wsl4ai.py` from GitHub to extract the remote `__version__`.
  3. If remote version is not superior, exits with no changes.
  4. With `--check`: prints available version and exits.
  5. If updating: clones repository to `.tmp/`, replaces `tool/`, cleans up. `conf/` is never touched.
- Output contract: plain text (not JSON — delegated to external script).
- **TUI**: not available; CLI-only.

```mermaid
flowchart LR
    subgraph CLI
        iu["wsl4ai install update\nwsl4ai iu [--check]"]
        cmd["install_update.cmd_install_update()"]
        iu --> cmd
    end
    subgraph Updater["conf/wsl4ai-update.py"]
        upd["os.execv → external script\ndownloads + replaces tool/"]
    end

    cmd -->|"os.execv"| upd
    upd --> stdout([stdout plain text])
```
