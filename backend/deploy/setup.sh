#!/usr/bin/env bash
# One-time bootstrap for a fresh Ubuntu Oracle Cloud Always Free instance
# (VM.Standard.E2.1.Micro: 1 OCPU, 1GB RAM). Run this once after creating
# the instance and SSH-ing in as ubuntu. Re-running is mostly safe but not
# the point — see deploy.sh for ongoing updates after this.
#
# Ubuntu-specific (apt-get, iptables) -- the current production backend
# instead runs on an Oracle Linux (dnf, firewalld) box set up by hand with
# the equivalent steps (Python 3.11 via `dnf module install`, Caddy via the
# @caddy/caddy copr repo, SELinux context fixes for systemd executing from
# $HOME). This script is kept for reference/for standing up a future Ubuntu
# instance, but wasn't used for that box.
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

echo "== OS-level firewall (iptables) =="
# Oracle's default Ubuntu image ships an iptables INPUT chain that only
# accepts SSH (port 22) and rejects everything else — independent of
# whatever the cloud console's Security List/NSG says. Both layers have to
# allow 80/443, or Let's Encrypt's HTTP-01 challenge fails with
# "Error getting validation data" and the cert never issues.
if ! sudo iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null; then
    sudo iptables -I INPUT 5 -p tcp --dport 80 -j ACCEPT
fi
if ! sudo iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null; then
    sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
fi
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save

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
echo "This script already opened the OS-level firewall (iptables) for the"
echo "same two ports — Oracle blocks at the cloud network level independent"
echo "of that, so both layers need it."

echo ""
echo "Done. Check status with: sudo systemctl status ipo-backend"
