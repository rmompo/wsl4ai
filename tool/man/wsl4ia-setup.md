# WSL4AI SETUP

Installation is handled by the **bootstrap installer** (`install/install.sh`). Manual setup is not required under normal circumstances.

---

## Automated install (recommended)

Place `install.sh` in `/tmp/wsl4ai/` and run as root:

```bash
mkdir -p /tmp/wsl4ai
curl -fsSL https://raw.githubusercontent.com/rmompo/wsl4ai/main/install/install.sh -o /tmp/wsl4ai/install.sh
sudo bash /tmp/wsl4ai/install.sh
```

The installer prompts for:

1. **`WSL4AI_USER`** — Linux account to create (password = username).
2. **`WSL_BASE`** — default `/home/<WSL4AI_USER>/wsl4ai/`.
3. **`HOST_DDBB`** — Windows path to the shared ddbb folder.
4. **`HOST_PROJECTS`** — Windows base path for projects.

After installation:

- The `wsl4ai` alias is available in every new Bash session.
- Each session start runs `wsl4ai use disableall --quiet` for safety.
- **Exit the WSL session and run `wsl --shutdown` from Windows** to apply all changes.

Full installer specification: [`specs/install/installer.md`](../../specs/install/installer.md).

---

## Runtime identity (`machine`, `user`)

The CLI resolves identity automatically — no flags needed:

- **`machine`**: Contents of `/etc/machine-id` (lowercase hex). Fallback on Windows: `win:<COMPUTERNAME>`.
- **`user`**: From `getpass.getuser()` (effective login name).

Unique identity is the pair `(machine, user)`.

---

## Path configuration (`local.env`)

Located at **`<WSL_TOOL>/local.env`** (next to `wsl4ai.py`). Written by the installer.

| Variable | Role |
| -------- | ---- |
| `WSL_BASE` | Base directory of the WSL4AI installation |
| `WSL_DDBB` | Path to the shared database directory |
| `WSL_TOOL` | Path to the tool directory |
| `WSL_PROJECTS` | WSL-side base path for projects |
| `HOST_DDBB` | Windows path to the shared ddbb folder |
| `HOST_PROJECTS` | Windows base path for projects |
| `HOST_DDBB_WSL` | `/mnt/...` translation of `HOST_DDBB` |

`HOST_PROJECTS` and `WSL_PROJECTS` are read at runtime by the tool to resolve absolute paths for registry operations (`registry add`, `registry list`, `use enable`, `use disable`, `start`). There is no `parameters` database table.

---

## `.bashrc` additions

The installer adds the following to the new user's `.bashrc` in order:

```bash
export PATH="${HOME}/.local/bin:${PATH}"   # pip --user scripts
cd ~                                        # start in home
alias wsl4ai="python3 <WSL_TOOL>/wsl4ai.py"
wsl4ai use disableall --quiet              # safety on session start
echo ""
echo "WSL4AI ready"
echo "  cli: wsl4ai <command>"
echo "  tui: wsl4ai tui"
echo ""
```
