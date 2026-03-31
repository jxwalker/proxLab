# proxlab

VM orchestration for your home lab — spin Proxmox VMs up/down, allocate TrueNAS NAS storage, and provision Postgres databases from a CLI, REST API, or web dashboard.

## Infrastructure

| Component | Address | Notes |
|---|---|---|
| Proxmox (`beast`) | `192.168.8.197:8006` | VMs managed in VMID range 200–299 |
| TrueNAS SCALE | `192.168.8.198` | Pool: `bigpool`, proxlab datasets under `bigpool/proxlab/` |
| nginx proxy | `192.168.8.220` | Reverse proxy to proxlab LXC |
| proxlab LXC | TBD after deploy | Runs API (port 8000) + web (port 3000) |

## Quick start (using proxlab itself to deploy proxlab)

### 1. Prerequisites on Proxmox (`beast`)

Create a dedicated API user and token:
```bash
# On beast, as root:
pveum useradd proxlab@pve -comment "proxlab orchestration"
pveum aclmod / -user proxlab@pve -role PVEAdmin
pveum user token add proxlab@pve proxlab --privsep=0
# Note the token UUID returned
```

Create the Postgres LXC first (proxlab needs a DB to provision DBs):
```bash
# Find and download the Ubuntu 24.04 LTS template
pveam update
pveam available --section system | grep ubuntu-24   # note exact filename
pveam download local ubuntu-24.04-standard_24.04-2_amd64.tar.zst

# Create postgres LXC (adjust template filename to match what pveam showed)
# --rootfs uses local-lvm (LVM thin) or local-zfs if your node uses ZFS
# 'local' storage does not support container directories
pct create 150 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname postgres --memory 512 --cores 1 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --rootfs local-lvm:8 --unprivileged 1 --start 1

# Get a shell inside the container — two options:
#
# Option A: Proxmox web UI
#   https://192.168.8.197:8006 → click LXC 150 in the tree → Console
#
# Option B: SSH into beast then enter the container
#   ssh root@192.168.8.197
#   pct enter 150

apt-get update && apt-get install -y postgresql
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'yourpassword';"

# Find the IP assigned to this LXC (you'll need it for POSTGRES_DSN)
ip addr show eth0 | grep 'inet '

exit  # back to beast
```
Note the IP shown — you'll use it as:
```
POSTGRES_DSN=postgresql://postgres:yourpassword@<LXC-IP>/postgres
```

### 2. Configure `.env`

```bash
cp .env.example .env
# Edit .env — fill in PROXMOX_TOKEN_VALUE, TRUENAS_API_KEY,
# POSTGRES_DSN (using postgres LXC IP), and PROXLAB_API_TOKEN
python3 -c "import secrets; print(secrets.token_hex(32))"  # generate PROXLAB_API_TOKEN
```

### 3. Create the proxlab LXC and deploy

```bash
# Create proxlab LXC on beast (same Ubuntu 24.04 template)
pct create 151 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname proxlab --memory 512 --cores 1 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --rootfs local-lvm:8 --unprivileged 1 --features nesting=1 --start 1

# Get a shell inside the container:
#   Option A: Proxmox web UI → click LXC 151 → Console
#   Option B: ssh root@192.168.8.197 then: pct enter 151

apt-get update && apt-get install -y docker.io docker-compose-plugin git

git clone https://github.com/jxwalker/proxLab.git /opt/proxlab
cd /opt/proxlab
cp .env.example .env

# Edit .env with your actual values:
#   PROXMOX_TOKEN_VALUE  — from the pveum token add output
#   TRUENAS_API_KEY      — from TrueNAS UI: System > API Keys > Add
#   POSTGRES_DSN         — postgresql://postgres:yourpassword@<postgres-LXC-IP>/postgres
#   PROXLAB_API_TOKEN    — run: python3 -c "import secrets; print(secrets.token_hex(32))"
nano .env

docker compose up -d

# Verify it started:
docker compose ps
curl http://localhost:8000/api/health

# Find this LXC's IP (for nginx config):
ip addr show eth0 | grep 'inet '

exit  # back to beast
```

### 4. Configure nginx proxy on `192.168.8.220`

```bash
# Copy the nginx config snippet
scp nginx-proxlab.conf user@192.168.8.220:/etc/nginx/sites-available/proxlab
# Edit PROXLAB_LXC_IP in the file, then:
ln -s /etc/nginx/sites-available/proxlab /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

Add to `/etc/hosts` on your dev machine:
```
192.168.8.220   proxlab.local
```

### 5. Configure the CLI

```bash
pip install -e cli/  # or: pipx install ./cli
proxlab config set --url http://proxlab.local/api --token <PROXLAB_API_TOKEN>
```

## CLI usage

```bash
# List all managed servers
proxlab vm list

# Spin up a dev server (small flavor, dev template)
proxlab vm create my-devbox --template dev --flavor small

# Spin up 3 dev servers at once with NAS storage and a database
proxlab vm create collab --template dev --flavor medium \
  --storage collab-data --db collabdb --count 3

# SSH into a running server (auto-resolves IP)
proxlab vm ssh 200

# Stop / destroy
proxlab vm stop 200
proxlab vm destroy 200 --yes

# NAS storage
proxlab storage list
proxlab storage create myproject --quota 100

# Databases
proxlab db create myapp
proxlab db info myapp   # prints DSN
proxlab db drop myapp --yes
```

## Web UI

Navigate to `http://proxlab.local` — dark dashboard with:
- **Dashboard** — live stats (running/stopped servers, NAS usage, DB count)
- **Servers** — sortable table with inline start/stop/destroy
- **Launch** — 3-step wizard: pick flavor → configure → review & launch (supports batch count)
- **Storage** — allocate TrueNAS ZFS datasets with NFS export
- **Databases** — create Postgres DBs, copy connection string in one click

## REST API

Interactive docs at `http://proxlab.local/docs` (FastAPI auto-generated).

Key endpoints (OpenStack Nova-style):

```
GET    /api/servers           # list proxlab VMs
POST   /api/servers           # provision a server (async)
POST   /api/servers/batch     # provision multiple servers
GET    /api/servers/{id}      # inspect (includes IP from guest agent)
DELETE /api/servers/{id}      # stop + destroy
POST   /api/servers/{id}/action  # {"action": "os-start|os-stop|os-reboot"}

GET    /api/flavors           # micro/small/medium/large/xlarge

GET    /api/storage           # list proxlab NAS datasets
POST   /api/storage           # allocate dataset + NFS export
DELETE /api/storage/{name}

GET    /api/databases
POST   /api/databases         # create DB + user, returns DSN
GET    /api/databases/{name}
DELETE /api/databases/{name}

GET    /api/tasks/{id}        # poll async task status
GET    /api/health
```

All endpoints require `Authorization: Bearer <PROXLAB_API_TOKEN>` except `/api/flavors` and `/api/health`.

## VM Templates

Two cloud-init templates in `templates/`:

| Template | Boot time | Contents |
|---|---|---|
| `base` | ~20s | Ubuntu 24.04 + qemu-guest-agent + Tailscale |
| `dev` | ~3min first boot | base + zsh/oh-my-zsh, starship, tmux, neovim/LazyVim, git delta, lazygit, gh CLI, fzf, ripgrep, bat, eza, zoxide, nvm, pyenv, go, rustup, docker |

### Building the base Proxmox template (VMID 9000)

Run once on `beast`:
```bash
# Download Ubuntu 24.04 cloud image
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img \
  -O /tmp/ubuntu-24.04-cloud.img

qm create 9000 --name proxlab-base --memory 1024 --cores 1 --net0 virtio,bridge=vmbr0
qm importdisk 9000 /tmp/ubuntu-24.04-cloud.img vmdata
qm set 9000 --scsihw virtio-scsi-pci --scsi0 vmdata:vm-9000-disk-0
qm set 9000 --ide2 vmdata:cloudinit --boot c --bootdisk scsi0
qm set 9000 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1
qm template 9000
```

## Development

```bash
# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
PROXMOX_TOKEN_VALUE=x TRUENAS_API_KEY=x POSTGRES_DSN=postgresql://u:p@h/db PROXLAB_API_TOKEN=x \
  uvicorn api.main:app --reload

# Tests
pytest tests/ -v

# Frontend
cd web && npm install && npm run dev
# Proxies /api/* to localhost:8000

# Docker (production)
docker compose up --build
```

## Architecture

```
proxlab LXC (on beast)
├── docker compose
│   ├── api  (FastAPI, :8000)  — wraps Proxmox + TrueNAS + Postgres APIs
│   └── web  (nginx+React, :3000) — static SPA
└── proxlab.local (via nginx at 192.168.8.220)
    ├── /api/*  → api:8000
    └── /*      → web:3000
```

Protected datasets (proxlab will never touch these):
- `bigpool/vmdata` — Proxmox VM disk storage
- `bigpool/models` — LLM model weights
