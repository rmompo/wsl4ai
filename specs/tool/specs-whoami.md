# Specification: `wsl4ai whoami` / `wsl4ai wai`

Runtime identity introspection command.

---

## 1. Purpose

Return the current runtime identity values:

- `machine` (runtime identifier)
- `user` (effective account)

---

## 2. Options

- None.

---

## 3. Output contract

- Always `output.result`
- Includes `output.data.rows` with one record containing:
  - `machine`
  - `user`

Although this is not a `list` command, it is treated as a data query by design.

