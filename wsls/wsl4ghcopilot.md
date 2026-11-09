# WSL setup: GitHub Copilot CLI

Target: Linux / Ubuntu WSL distro.

---

## 1. Install GitHub Copilot CLI

Run the script shipped with WSL4AI (it refuses to run if Claude Code is already installed: one AI client per distro):

```bash
bash ~/wsl4ai/tool/scripts/wsl4ai-install-ghcopilot.sh
```

It runs the standalone installer, which needs no Node.js or Homebrew:

```bash
curl -fsSL https://gh.io/copilot-install | bash
```

Verify:

```bash
copilot --version
```

---

## 2. Authenticate

On first run, GitHub Copilot CLI asks you to log in with your GitHub account:

```bash
copilot
```

Follow the prompts (choose `GitHub.com` and authenticate via browser).

---

## 3. Apply changes

`~/.local/bin` is already on the PATH through `~/.startup-wsl4ai.sh`. If the command is not found, reload your shell:

```bash
source ~/.bashrc
```

Or exit and reopen the WSL terminal.
