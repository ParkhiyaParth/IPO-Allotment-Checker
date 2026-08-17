#!/usr/bin/env bash
# One-time bootstrap for a fresh Oracle Cloud Always Free instance
# (VM.Standard.E2.1.Micro: 1 OCPU, 1GB RAM). Run this once after creating
# the instance and SSH-ing in as ubuntu. Re-running is mostly safe but not
# the point — see deploy.sh for ongoing updates after this.
set -euo pipefail

REPO_URL="https://github.com/ParkhiyaParth/IPO-Allotment-Checker.git"
APP_DIR="$HOME/IPO-Allotment-Checker"

echo "== Swap file (1GB RAM needs the headroom) =="
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
else
    echo "swapfile already exists, skipping"
fi

echo "== System packages =="
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git curl debian-keyring debian-archive-keyring apt-transport-https

echo "== Caddy (reverse proxy + automatic HTTPS) =="
if ! command -v caddy >/dev/null; then
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt-get update -y
    sudo apt-get install -y caddy
else
    echo "caddy already installed, skipping"
fi

echo "== Clone repo =="
if [ ! -d "$APP_DIR" ]; then
    git clone "$REPO_URL" "$APP_DIR"
else
    echo "repo already cloned at $APP_DIR, skipping clone"
fi

echo "== Python venv + dependencies =="
cd "$APP_DIR/backend"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "== systemd service =="
sudo cp deploy/ipo-backend.service /etc/systemd/system/ipo-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now ipo-backend

echo "== Caddy config =="
echo "!! Edit backend/deploy/Caddyfile to put in this instance's real IP"
echo "   (dashes instead of dots, e.g. 129-154-10-20.sslip.io), then run:"
echo "     sudo cp $APP_DIR/backend/deploy/Caddyfile /etc/caddy/Caddyfile"
echo "     sudo systemctl reload caddy"

echo ""
echo "== Also required: Oracle Cloud Security List =="
echo "In the OCI console, add Ingress Rules for this instance's subnet:"
echo "  - 0.0.0.0/0 -> TCP port 80  (Let's Encrypt HTTP challenge)"
echo "  - 0.0.0.0/0 -> TCP port 443 (HTTPS)"
echo "The instance's own OS firewall (iptables/ufw) is separate from this"
echo "and often the one people forget — Oracle blocks at the cloud network"
echo "level regardless of what the OS firewall allows."

echo ""
echo "Done. Check status with: sudo systemctl status ipo-backend"
