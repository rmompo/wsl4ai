# WSL setup: Homebrew + GitHub Copilot CLI

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
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```

Verify:

```bash
brew --version
```

---

## 3. Install GitHub Copilot CLI

```bash
brew install gh
gh extension install github/gh-copilot
```

Verify:

```bash
gh copilot --version
```

---

## 4. Authenticate

```bash
gh auth login
```

Follow the prompts to log in with your GitHub account. Choose `GitHub.com` and authenticate via browser.

---

## 5. Usage

```bash
gh copilot suggest "list all running docker containers"
gh copilot explain "sudo apt-get update && sudo apt-get upgrade -y"
```

---

## 6. Apply changes

Reload your shell if needed:

```bash
source ~/.bashrc
```

Or exit and reopen the WSL terminal.
