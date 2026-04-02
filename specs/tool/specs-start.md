# Specification: `wsl4ai start`

Launch one concrete mounted `use` in the current terminal session.

---

## 1. Purpose

`start` resolves a single `uses` link, changes directory to the resolved WSL path for that link, and executes the target WSL `cli_command`.

---

## 2. Inputs and target resolution

- Required selector (exactly one):
  - `-ru` / `--registry-uuid`
  - `-rn` / `--registry-name`
- Optional WSL selector (at most one):
  - `-wu` / `--wsl-uuid`
  - `-wn` / `--wsl-name`
- If WSL selector is omitted, runtime identity resolution is used (`RuntimeIdentity` -> runtime `wsl_name` + runtime `user`).

This identifies one concrete `use`: (`wsl_uuid`, `registry_uuid`).

---

## 3. Security and execution rules (normative)

1. The `use` row must exist; otherwise fail.
2. The `use` row must have `mounted = 1`; otherwise fail (security gate).
3. The working directory is resolved as:
   - `WSL_PROJECTS` (from `local.env`) + `rel_path_wsl` (from selected `registry`).
4. `wsls.cli_command` for the resolved `wsl_uuid` must be non-empty; otherwise fail.
5. Execution mode is foreground in the same terminal session (not detached).
6. TUI-triggered `start` also runs in the same console session.

Path resolution uses `load_local_env_paths()` from `common.py` (reads `WSL_PROJECTS` from `local.env`).

The command is fail-closed: any missing/invalid dependency prevents execution.

---

## 4. Output contract

- Always `output.result`
- No `output.data` (action command, non-query)
- `output.result.status`:
  - `0` when command exits successfully
  - non-zero for validation errors or subprocess failure
