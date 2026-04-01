# WSL4AI command reference

CLI reference only: what each subcommand does, flags, and examples. For prerequisites, installation, and environment setup, see **`wsl4ia-setup.md`**.

Use `wsl4ai <command> --help` for argparse details.

## Runtime fields (automatic)

Handlers receive **`machine`**, **`user`**, and **`runtime_identity`** (includes **`wsl_name`** for WSL resolution) on `args`; they are **not** CLI flags (filled in `main()` before the handler runs). Semantics are documented in **`wsl4ia-setup.md`** and **`wsl4ai/specs/specs.md`** §1.6.

## Command shortcuts

Same behavior as the long form; see **`wsl4ai/specs/specs.md`** §4.

| Long | Under `registry` / `use` | Top-level |
| ----- | ------------------------ | --------- |
| `registry list` | `registry rl` | `wsl4ai rl` |
| `registry add` | `registry ra` | `wsl4ai ra` |
| `registry remove` | `registry rr` | `wsl4ai rr` |
| `use add` | `use ua` | `wsl4ai ua` |
| `use list` | `use ul` | `wsl4ai ul` |
| `use remove` | `use ur` | `wsl4ai ur` |
| `use enable` | `use ue` | `wsl4ai ue` |
| `use disable` | `use ud` | `wsl4ai ud` |
| `use disableall` | `use uda` | `wsl4ai uda` |
| `wsl list` | `wsl wl` | `wsl4ai wl` |
| `wsl set` | — | `wsl4ai ws` |
| `whoami` | — | `wsl4ai wai` |
| `install tool` | — | `wsl4ai it` |
| `install database` | — | `wsl4ai id` |
| `install alias` | — | `wsl4ai ia` |

---

## 1. Commands

### 1.a `whoami`

Prints the runtime **`machine`** and **`user`** strings (see **`wsl4ai/specs/specs.md`** §1 and §6) — the same values other commands receive on `args`. **No database required** — no arguments or flags.

```bash
wsl4ai whoami
```

Example output (shape only):

```text
machine: dcbb4f2e3e5f4a1b9c8d7e6f5a4b3c2d
user: alice
```

### 1.b `registry list`

Subcommand of **`registry`**. Lists **registry** as the identity: each block is `name (uuid)`, then **`host:`** and **`wsl:`** as **fully resolved paths** (bases from `parameters` with **`expand_path_template`**, joined to each row’s relative segments with **`os.path.join`** / **`normpath`**, same as **`registry add`**). If any **`uses`** row links that registry to a **`wsls`** row, one indented line per link: `- wsl.name/wsl.user (wsl.uuid) mounted={0|1}`.

On a **TTY**, the registry title line uses a **red** background when linked (busy) and **green** when not; plain text if output is piped or **`NO_COLOR`** is set.

Requires an existing database file (see **`install --database`**). Full rules: **`wsl4ai/specs/specs-registry.md`**.

```bash
wsl4ai registry list
```

### 1.c `registry add`

Subcommand of **`registry`**. Inserts one row into **`registries`** only. Requires an existing database file. By default, for each side, the base from `parameters` is expanded with **`expandvars`** and **`expanduser`**, then joined to the flag value with **`os.path.join`** (no manual `/` between base and segment), and **both** resulting paths must exist on disk before insert. With **`--force`**, those existence checks are skipped. Full rules: **`wsl4ai/specs/specs-registry.md`**.


| Flag     | Meaning                                                                                        |
| -------- | ---------------------------------------------------------------------------------------------- |
| `--name` | Logical name; **unique in `registries` ignoring case** (`Foo` clashes with `foo`). **Required.** |
| `--host` | Path segment joined under `base_path_host` (`parameters`). **Required.**                            |
| `--wsl`  | Path segment joined under `base_path_wsl` (`parameters`). **Required.**                           |
| `--force` | Do **not** verify that the resolved host and WSL paths exist. **Optional.**                   |


```bash
wsl4ai registry add --name myproj --host projects/foo --wsl work/foo
wsl4ai registry add --name myproj --host projects/foo --wsl work/foo --force
```

### 1.d `registry remove`

Subcommand of **`registry`**. Deletes one row from **`registries`** **only if** there are **no** **`uses`** rows for that registry (remove links with **`use remove`** first). **At least one** of **`--uuid`** or **`--name`** is required. If both are given, only **`--uuid`** is used for lookup. Full rules: **`wsl4ai/specs/specs-registry.md`**.


| Flag | Meaning |
| ----- | -------- |
| `--uuid` | Registry UUID. |
| `--name` | Logical name (**case-insensitive** match). |
| *(one required)* | Pass `--uuid` and/or `--name`; not both empty. |


```bash
wsl4ai registry remove --name myproj
wsl4ai registry remove --uuid 550e8400-e29b-41d4-a716-446655440000
```

### 1.e `use`

Router for usage links between **`wsls`** and **`registries`**. Subcommands: **`list`**, **`add`**, **`remove`**, **`enable`**, **`disable`**, **`disableall`** (shortcuts **`ul`**, **`ua`** … **`uda`**). Typical flags: **`--registry-uuid`** or **`--registry-name`**; optional **`--wsl-uuid`** / **`--wsl-name`** (if omitted, runtime WSL identity is used). `use list` also supports **`-a/--all`** for global read-only listing. **`enable`** / **`disable`** set **`uses.mounted`** to 1 or 0. Full rules: **`wsl4ai/specs/specs-use.md`**.

```bash
wsl4ai use list
wsl4ai use list -a
wsl4ai use list --wsl-name Ubuntu
wsl4ai use add --registry-name myproj
wsl4ai use remove --registry-name myproj
wsl4ai ul
wsl4ai ul -a
wsl4ai ua --registry-name myproj
```

### 1.f `wsl` / `ws`

Router for WSL rows. Subcommands:

- **`list`**: show tracked `wsls` rows.
- **`set`**: update **`wsls.cli_command`** for an existing WSL row (`--cli` required; optional `--wsl-uuid/--wsl-name`, default runtime WSL).

Top-level shortcuts:

- **`wsl4ai wl`** = `wsl4ai wsl list`
- **`wsl4ai ws`** = `wsl4ai wsl set`

```bash
wsl4ai wsl list
wsl4ai wl
wsl4ai wsl set --cli "echo ok"
wsl4ai wsl set --cli "echo ok" --wsl-name Ubuntu
wsl4ai ws --cli "echo ok"
```

### 1.g `start`

Runs one concrete mounted `use` in the current terminal session.

- Select target by `--registry-uuid` or `--registry-name` (required).
- Optional `--wsl-uuid` / `--wsl-name`; if omitted, runtime WSL is used.
- Security gate: only runs when the target `use` has `mounted=1`.
- Working directory is resolved as `base_path_wsl + rel_path_wsl`.
- Executes the resolved WSL `cli_command` in foreground (not detached).

```bash
wsl4ai start --registry-name myproj
wsl4ai start --registry-uuid 550e8400-e29b-41d4-a716-446655440000 --wsl-name Ubuntu
```

### 1.h `tui`

Interactive text user interface with arrow navigation, submenu flow, and prompt-based forms. TUI actions are runtime-local (no WSL selector prompts, no global `-a/--all` exposure in menus). `Start` runs in the same terminal session (foreground, non-detached).

```bash
wsl4ai tui
```

---

## 2. Special commands

Special router: **`install`** with subcommands:

- **`install tool`** (`it`): ensure tool layout.
- **`install database`** (`id`): create DB if missing; with `-f/--force`, recreate.
- **`install alias`** (`ia`): add/remove aliases in shell profiles.

### 2.a `install tool`

No options.

```bash
wsl4ai install tool
wsl4ai it
```

### 2.b `install database`

| Option | Meaning |
| ------ | ------- |
| `-f`, `--force` | Recreate database content if the file already exists (destructive). |

```bash
wsl4ai install database
wsl4ai install database --force
wsl4ai id
```

### 2.c `install alias`

Required options:

| Option | Meaning |
| ------ | ------- |
| `-a`, `--action` | `add` or `remove` |
| `-t`, `--type` | `ps` or `bash` |
| `-n`, `--name` | Alias name (repeatable) |

Rules:

- add: if alias already exists, return error.
- remove: if alias does not exist, return error.

```bash
wsl4ai install alias -a add -t bash -n wsl4ai -n myw
wsl4ai ia -a remove -t ps -n wsl4ai
```
