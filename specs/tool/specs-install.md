# Specification: `wsl4ai install ...`

Command group for setup and shell integration tasks.

---

## 1. Subcommands

- `install tool` (`it`)
- `install database` (`id`)
- `install alias` (`ia`)
- `install update` (`iu`)

---

## 2. `install tool`

- Purpose: install/verify tool layout.
- Options: none.
- Output contract:
  - Always `output.result`
  - No `output.data` (non-query operation)

---

## 3. `install database`

- Purpose: initialize database or reset it.
- Options:
  - Optional `-f` / `--force` for destructive overwrite.
- Output contract:
  - Always `output.result`
  - No `output.data` (non-query operation)

---

## 4. `install alias`

- Purpose: add/remove aliases in shell profile targets.
- Required options:
  - `-a` / `--action` -> `add|remove`
  - `-t` / `--type` -> `ps|bash`
  - `-n` / `--name` -> repeatable alias names
- Validation rules:
  - `add`: existing alias -> error
  - `remove`: missing alias -> error
  - Alias status is treated as one logical unit per alias name.
- Output contract:
  - Always `output.result`
  - No `output.data` (non-query operation)

---

## 5. `install update`

- Purpose: check for and apply a new version of the tool from GitHub.
- Options:
  - Optional `--check` — print available version without applying the update.
- Behavior:
  1. Delegates immediately to `conf/wsl4ai-update.py` via `os.execv` (the standalone updater is never replaced by updates).
  2. The updater downloads `wsl4ai.py` from GitHub raw to extract the remote `__version__`.
  3. If the remote version is not superior to the local one, exits with no changes.
  4. With `--check`: prints the available version and exits.
  5. If updating: clones the full repository to `.tmp/`, moves current `tool/` to `.tmp/old/`, moves new `tool/` into place, cleans up `.tmp/`.
  6. `conf/` is **never touched** during update.
- Output contract: plain text (not JSON envelope — delegated to external script).

