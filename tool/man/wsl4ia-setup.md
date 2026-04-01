# WSL4AI SETUP

Everything runs on the **WSL side** (your Linux distro).

Substitute `<username>` with the actual Linux username. Substitute `/path/to/wsl4ai` with the directory that contains the tool (bind mount, git clone, etc.).

## Requirements and dependencies

| Requirement | Notes |
| ----------- | ----- |
| **Environment** | WSL distro (Linux user space). Commands that edit Bash expect a normal user shell. |
| **Python** | **Python 3** on `PATH` as `python3`. |
| **`pip`** | Only needed if you choose to install optional dependencies from `requirements.txt`. |
| **`rich`** | Optional. The registered CLI no longer includes `man` (so `rich` is not required for core commands). |
| **Layout** | After clone/copy you should have `wsl4ai.py`, `commands/` (and `ddbb/` after **`install tool`** or manual create). `wsl4ai.py` refuses to start if `ddbb/` is missing next to the script. |
| **Database** | Optional until you use `registry list` / `registry add` / `registry remove`: run **`wsl4ai install database`** once to create `ddbb/wsl4ai.db` and seed **`parameters`** (`id` + `value` for `base_path_host` and `base_path_wsl`) (see **`wsl4ia-man.md`**). |

### `machine` and `user` (runtime)

The CLI does **not** pass `machine` or `user` as flags. Every handler receives them on `args`:

- **`machine`**: Preferred source is **`/etc/machine-id`** (or **`/var/lib/dbus/machine-id`**) inside Linux — one stable ID per root filesystem; two WSL instances can share the same distro *label* (`WSL_DISTRO_NAME`) but still differ here. **Fallback** if no id file (e.g. Windows host running Python): `wsl:<distro>:<node>` when `WSL_DISTRO_NAME` is set, else `win:<COMPUTERNAME>` / `platform.node()`, else `unknown`.
- **`user`**: From **`getpass.getuser()`** (login name / `whoami` for the current process).

Handlers may use `args.machine` as a stable key for this environment (DB, logs, future mount logic).

---

## 1. As root

Open a root shell (`sudo -i` or `su -`).

1. **Create the new user**

```bash
useradd -m -s /bin/bash <username>
passwd <username>
```

2. **Grant sudo**

```bash
usermod -aG sudo <username>
```

3. **Create `~/wsl4ai` for that user**

```bash
mkdir -p /home/<username>/wsl4ai
chown <username>:<username> /home/<username>/wsl4ai
```

4. **Copy the tool into the user's home**

```bash
cp -r /path/to/wsl4ai/. /home/<username>/wsl4ai/
chown -R <username>:<username> /home/<username>/wsl4ai
```

5. **(Optional) Default user for this distro**

```bash
printf "[user]\ndefault=<username>\n" > /etc/wsl.conf
```

Then on **Windows** (PowerShell or CMD) run `wsl --shutdown`, then start the distro again; you should log in as `<username>`.

## 2. As the new user

1. **Verify Python 3**

```bash
python3 --version
```

If `python3` is missing (`command not found`), install it (pick one that matches your distro):

**Debian / Ubuntu**

```bash
sudo apt update
sudo apt install -y python3
```

**Fedora**

```bash
sudo dnf install -y python3
```

**openSUSE**

```bash
sudo zypper install -y python3
```

Then run `python3 --version` again.

2. **(Optional) Install `rich`**

`rich` is only needed for the legacy/local manual renderer. The registered CLI commands do not require it.

If you still want it:

```bash
cd ~/wsl4ai
python3 -m pip install --user -r requirements.txt
```

(Replace `~/wsl4ai` with your real tool directory if different. Omit `--user` if you use a virtual environment and have already activated it.)

3. **Install the on-disk tool layout (required)**

`wsl4ai.py` only runs after `ddbb/` exists. Create the layout (including `ddbb/` and `man/`):

```bash
python3 ~/wsl4ai/wsl4ai.py install tool
```

4. **(Optional) Create the database**

```bash
python3 ~/wsl4ai/wsl4ai.py install database
```

5. **Install the Bash helper for `wsl4ai` (recommended)**

Registers a `wsl4ai` shell function that points at this script:

```bash
python3 ~/wsl4ai/wsl4ai.py install alias -a add -t bash -n wsl4ai
source ~/.bashrc
```

After this, the `wsl4ai` command is available in new Bash sessions (and in the current session after `source`).

## 3. Others

### Remove the Bash helper (`wsl4ai` function in `~/.bashrc`)

If the `wsl4ai` command works in your shell:

```bash
wsl4ai unalias --bash
source ~/.bashrc
```

If it does not (e.g. you removed the tool first), call the CLI directly:

```bash
python3 ~/wsl4ai/wsl4ai.py unalias --bash
source ~/.bashrc
```

This deletes the marked block WSL4AI adds between `# >>> WSL4AI BEGIN >>>` and `# <<< WSL4AI END <<<` in `~/.bashrc`.
