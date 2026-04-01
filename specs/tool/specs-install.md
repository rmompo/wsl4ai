# Specification: `wsl4ai install ...`

Command group for setup and shell integration tasks.

---

## 1. Subcommands

- `install tool` (`it`)
- `install database` (`id`)
- `install alias` (`ia`)

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

