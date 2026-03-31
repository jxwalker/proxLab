# proxlab

VM orchestration for your home lab — spin Proxmox VMs up/down, allocate TrueNAS NAS storage, and provision Postgres databases from a CLI, REST API, or web dashboard.

## Infrastructure

| Component | Address | Notes |
|---|---|---|
| Proxmox (`beast`) | `192.168.8.197:8006` | VMs managed in VMID range 200–299 |
| TrueNAS SCALE | `192.168.8.198` | Pool: `bigpool`, proxlab datasets under `bigpool/proxlab/` |
| nginx proxy | `192.168.8.220` | Reverse proxy to proxlab LXC |
| proxlab LXC | TBD after deploy | Runs API (port 8000) + web (port 3000) |

## Deployment

### What you're building

Four things need to exist before proxlab works:

```
Your dev machine
  └── proxlab CLI (installed via pip)

beast (Proxmox, 192.168.8.197)
  ├── LXC 150  postgres    ← shared Postgres server for all provisioned VMs
  └── LXC 151  proxlab     ← runs the API + web dashboard (docker compose)

nginx (192.168.8.220)
  └── proxlab.local → proxlab LXC (port 8000 for API, port 3000 for web)
```

---

### Step 1 — On beast: create the Proxmox API token

SSH into beast (`ssh root@192.168.8.197`) and run:

```bash
# Create a dedicated proxlab user and API token
pveum useradd proxlab@pve -comment "proxlab orchestration"
pveum aclmod / -user proxlab@pve -role PVEAdmin
pveum user token add proxlab@pve proxlab --privsep=0
# ⚠️  Copy the token UUID shown — you won't see it again
```

Also download the Ubuntu 24.04 LXC template (used for both LXCs):

```bash
pveam update
pveam available --section system | grep ubuntu-24   # note exact filename
pveam download local ubuntu-24.04-standard_24.04-2_amd64.tar.zst
```

---

### Step 2 — On beast: create LXC 150 (Postgres)

Still on beast, create the Postgres container:

```bash
pct create 150 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname postgres --memory 512 --cores 1 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --rootfs local-lvm:8 --unprivileged 1 --start 1
```

> `local-lvm` is the correct storage for container disks. `local` only holds templates and ISOs.

Now enter the container shell. Two ways to do this:
- **Proxmox web UI**: `https://192.168.8.197:8006` → click **LXC 150** in the left tree → **Console**
- **From beast shell**: `pct enter 150`

```bash
# ---- Inside LXC 150 ----
apt-get update && apt-get install -y postgresql

# Set a password for the postgres superuser
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'yourpassword';"

# Note the IP — you'll need it for .env
ip addr show eth0 | grep 'inet '

exit  # back to beast
```

Make a note of the IP shown, e.g. `192.168.8.151`.

---

### Step 3 — On beast: create LXC 151 (proxlab app)

Back on beast, create the proxlab container:

```bash
pct create 151 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname proxlab --memory 512 --cores 1 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --rootfs local-lvm:8 --unprivileged 1 --features nesting=1 --start 1
```

> `nesting=1` is required for Docker to run inside an LXC.

Enter the container:
- **Proxmox web UI**: click **LXC 151** → **Console**
- **From beast shell**: `pct enter 151`

```bash
# ---- Inside LXC 151 ----
apt-get update && apt-get install -y docker.io docker-compose-plugin git

# Clone the repo
git clone https://github.com/jxwalker/proxLab.git /opt/proxlab
cd /opt/proxlab

# Create the .env file from the template
cp .env.example .env

# Generate a random API token for the proxlab API
python3 -c "import secrets; print(secrets.token_hex(32))"
# ← copy this output, paste it as PROXLAB_API_TOKEN below

# Edit .env and fill in all values:
nano .env
```

The values to fill in:

| Variable | Where to get it |
|---|---|
| `PROXMOX_TOKEN_VALUE` | Output of `pveum user token add` in Step 1 |
| `TRUENAS_API_KEY` | TrueNAS UI → System → API Keys → Add |
| `POSTGRES_DSN` | `postgresql://postgres:yourpassword@<LXC-150-IP>/postgres` |
| `PROXLAB_API_TOKEN` | The token you just generated above |

Once `.env` is filled in, start the app:

```bash
# ---- Still inside LXC 151 ----
docker compose up -d

# Verify both containers are running
docker compose ps

# Confirm the API responds
curl http://localhost:8000/api/health
# Expected: {"status": "ok", "service": "proxlab-api"}

# Note this LXC's IP — needed for nginx config
ip addr show eth0 | grep 'inet '

exit  # back to beast
```

---

### Step 4 — On nginx (192.168.8.220): configure the reverse proxy

```bash
# From your dev machine, copy the nginx config snippet
scp nginx-proxlab.conf user@192.168.8.220:/etc/nginx/sites-available/proxlab

# SSH into 192.168.8.220 and edit the config
ssh user@192.168.8.220
nano /etc/nginx/sites-available/proxlab
# Replace PROXLAB_LXC_IP with the IP from LXC 151

ln -s /etc/nginx/sites-available/proxlab /etc/nginx/sites-enabled/proxlab
nginx -t && systemctl reload nginx
exit
```

---

### Step 5 — On your dev machine: add hosts entry and install CLI

```bash
# Add to /etc/hosts so proxlab.local resolves
echo "192.168.8.220   proxlab.local" | sudo tee -a /etc/hosts

# Install the CLI
pip install -e /path/to/proxlab/cli
# or if you cloned the repo locally:
pip install -e cli/

# Point the CLI at your deployment
proxlab config set \
  --url http://proxlab.local/api \
  --token <your-PROXLAB_API_TOKEN>

# Test it
proxlab vm list
```

Web UI: open `http://proxlab.local` in your browser.

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
