#!/usr/bin/env bash
# proxlab dev template setup script
# Run once on first boot via cloud-init runcmd (as root, then switches to user)
# Installs a full developer toolchain for the default 'ubuntu' user
set -euo pipefail

DEV_USER="${1:-ubuntu}"
HOME_DIR="/home/${DEV_USER}"
export DEBIAN_FRONTEND=noninteractive

echo "==> proxlab dev setup for user: ${DEV_USER}"

# ---------------------------------------------------------------------------
# System packages
# ---------------------------------------------------------------------------
apt-get update -qq
apt-get install -y --no-install-recommends \
    build-essential git curl wget unzip zip \
    zsh tmux \
    jq ripgrep fd-find \
    fzf \
    postgresql-client \
    docker.io docker-compose-plugin \
    python3 python3-pip python3-venv \
    ca-certificates gnupg apt-transport-https \
    fontconfig

# ---------------------------------------------------------------------------
# Docker — add user to docker group
# ---------------------------------------------------------------------------
usermod -aG docker "${DEV_USER}"
systemctl enable --now docker

# ---------------------------------------------------------------------------
# bat (cat with syntax highlighting) — Ubuntu ships as 'batcat'
# ---------------------------------------------------------------------------
apt-get install -y bat
ln -sf /usr/bin/batcat /usr/local/bin/bat || true

# ---------------------------------------------------------------------------
# eza (modern ls)
# ---------------------------------------------------------------------------
EZA_VERSION=$(curl -s https://api.github.com/repos/eza-community/eza/releases/latest | jq -r '.tag_name')
curl -fsSL "https://github.com/eza-community/eza/releases/download/${EZA_VERSION}/eza_x86_64-unknown-linux-musl.tar.gz" \
  | tar -xz -C /usr/local/bin

# ---------------------------------------------------------------------------
# delta (better git diffs)
# ---------------------------------------------------------------------------
DELTA_VERSION=$(curl -s https://api.github.com/repos/dandavison/delta/releases/latest | jq -r '.tag_name')
DELTA_DEB="git-delta_${DELTA_VERSION}_amd64.deb"
curl -fsSL "https://github.com/dandavison/delta/releases/download/${DELTA_VERSION}/${DELTA_DEB}" -o /tmp/delta.deb
dpkg -i /tmp/delta.deb && rm /tmp/delta.deb

# ---------------------------------------------------------------------------
# lazygit (TUI git client)
# ---------------------------------------------------------------------------
LAZYGIT_VERSION=$(curl -s https://api.github.com/repos/jesseduffield/lazygit/releases/latest | jq -r '.tag_name' | sed 's/v//')
curl -fsSL "https://github.com/jesseduffield/lazygit/releases/download/v${LAZYGIT_VERSION}/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz" \
  | tar -xz -C /usr/local/bin lazygit

# ---------------------------------------------------------------------------
# gh (GitHub CLI)
# ---------------------------------------------------------------------------
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
  https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list
apt-get update -qq && apt-get install -y gh

# ---------------------------------------------------------------------------
# zoxide (smart cd)
# ---------------------------------------------------------------------------
curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh

# ---------------------------------------------------------------------------
# starship prompt
# ---------------------------------------------------------------------------
curl -sS https://starship.rs/install.sh | sh -s -- --yes

# ---------------------------------------------------------------------------
# neovim (AppImage)
# ---------------------------------------------------------------------------
NVIM_VERSION=$(curl -s https://api.github.com/repos/neovim/neovim/releases/latest | jq -r '.tag_name')
curl -fsSL "https://github.com/neovim/neovim/releases/download/${NVIM_VERSION}/nvim-linux-x86_64.appimage" \
  -o /usr/local/bin/nvim
chmod +x /usr/local/bin/nvim

# ---------------------------------------------------------------------------
# yq (YAML processor)
# ---------------------------------------------------------------------------
YQ_VERSION=$(curl -s https://api.github.com/repos/mikefarah/yq/releases/latest | jq -r '.tag_name')
curl -fsSL "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" \
  -o /usr/local/bin/yq && chmod +x /usr/local/bin/yq

# ---------------------------------------------------------------------------
# httpie (modern curl)
# ---------------------------------------------------------------------------
pip3 install httpie --quiet

# ---------------------------------------------------------------------------
# Run user-level setup as the dev user
# ---------------------------------------------------------------------------
sudo -u "${DEV_USER}" bash -s "${DEV_USER}" "${HOME_DIR}" << 'USERSETUP'
DEV_USER="$1"
HOME_DIR="$2"

# zsh as default shell
sudo chsh -s /usr/bin/zsh "${DEV_USER}"

# oh-my-zsh
export RUNZSH=no
export CHSH=no
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# zsh plugins: zsh-autosuggestions, zsh-syntax-highlighting
git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions \
  "${HOME_DIR}/.oh-my-zsh/custom/plugins/zsh-autosuggestions"
git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting \
  "${HOME_DIR}/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting"

# Write .zshrc
cat > "${HOME_DIR}/.zshrc" << 'ZSHRC'
export ZSH="$HOME/.oh-my-zsh"
plugins=(git z fzf docker zsh-autosuggestions zsh-syntax-highlighting)
source $ZSH/oh-my-zsh.sh

# Aliases
alias ls='eza --icons'
alias ll='eza -lah --icons'
alias cat='bat'
alias lg='lazygit'
alias vim='nvim'
alias vi='nvim'
alias k='kubectl'

# zoxide
eval "$(zoxide init zsh)"

# starship
eval "$(starship init zsh)"

# nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# pyenv
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# go
export PATH="$PATH:/usr/local/go/bin:$HOME/go/bin"

# cargo
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

ZSHRC

# tmux config
cat > "${HOME_DIR}/.tmux.conf" << 'TMUXCONF'
set -g prefix C-a
unbind C-b
bind C-a send-prefix

set -g mouse on
set -g default-terminal "screen-256color"
set -g history-limit 50000
set -g status-style bg=colour234,fg=colour137
set -g status-left '#[fg=colour39,bold] #H '
set -g status-right '#[fg=colour39] %H:%M %d-%b '
set -g base-index 1
setw -g pane-base-index 1

# Split panes with | and -
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"

# Reload config
bind r source-file ~/.tmux.conf \; display "Reloaded!"
TMUXCONF

# git delta config
git config --global core.pager delta
git config --global delta.navigate true
git config --global delta.light false
git config --global delta.side-by-side true
git config --global interactive.diffFilter "delta --color-only"

# nvm + Node LTS
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
export NVM_DIR="${HOME_DIR}/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install --lts
nvm alias default 'lts/*'

# pyenv + Python 3.12
curl https://pyenv.run | bash
export PYENV_ROOT="${HOME_DIR}/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
pyenv install 3.12 --skip-existing
pyenv global 3.12

# rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path

# LazyVim (neovim distro)
rm -rf "${HOME_DIR}/.config/nvim"
git clone --depth=1 https://github.com/LazyVim/starter "${HOME_DIR}/.config/nvim"
rm -rf "${HOME_DIR}/.config/nvim/.git"

USERSETUP

# ---------------------------------------------------------------------------
# Go (system-wide latest)
# ---------------------------------------------------------------------------
GO_VERSION=$(curl -s https://go.dev/VERSION?m=text | head -1)
curl -fsSL "https://go.dev/dl/${GO_VERSION}.linux-amd64.tar.gz" \
  | tar -xz -C /usr/local

echo "==> proxlab dev setup complete for ${DEV_USER}"
