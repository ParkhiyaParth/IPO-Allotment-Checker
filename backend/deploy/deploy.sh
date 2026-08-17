#!/usr/bin/env bash
# Redeploys the backend to its latest pushed state. Runs on the server
# itself — GitHub Actions SSHs in and invokes this after every push to
# main. Safe to run manually too.
set -euo pipefail

APP_DIR="$HOME/IPO-Allotment-Checker"

cd "$APP_DIR"
git fetch origin main
git reset --hard origin/main

cd "$APP_DIR/backend"
.venv/bin/pip install -r requirements.txt

sudo systemctl restart ipo-backend
sudo systemctl --no-pager status ipo-backend
