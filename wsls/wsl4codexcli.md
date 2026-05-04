# WSL setup: Homebrew + Codex + Bubblewrap

Target: Linux / Ubuntu WSL distro.

---

## 1. Install build tools (Homebrew requirement)

Homebrew on Linux requires GCC and basic build utilities:

```bash
sudo apt-get install -y build-essential procps curl file git
```

---

## 2. Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After the installer finishes, follow the printed instructions to add Homebrew to your PATH. Typically:

```bash
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```

Verify:

```bash
brew --version
```

---

## 3. Install Codex

```bash
brew install codex
```

Verify:

```bash
codex --version
```

---

## 4. Install Bubblewrap

Codex uses `bubblewrap` for sandboxing. Install it via apt:

```bash
sudo apt-get install -y bubblewrap
```

Without it, Codex falls back to a vendored binary and prints a warning on startup. Installing it eliminates that warning.

---

## 5. Configure startup script

Insert it into `~/.bashrc` just above the `.startup-wsl4ai.sh` line:

```bash
sed -i 's|source ~/.startup-wsl4ai.sh|source ~/wsl4ai/extras/.startup-codex.sh\nsource ~/.startup-wsl4ai.sh|' ~/.bashrc
```

The `.startup-codex.sh` script runs `brew update` and `brew upgrade codex` silently on each session start, keeping Codex up to date automatically.

---

## 6. Apply changes

Reload your shell:

```bash
source ~/.bashrc
```

Or exit and reopen the WSL terminal.
