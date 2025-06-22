#!/bin/bash
set -e

APP_USER="lnmt"
APP_GROUP="lnmt"

echo "== Creating config and data directories =="
sudo mkdir -p /etc/lnmt
sudo mkdir -p /usr/local/lib/lnmt

echo "== Creating lnmt system user and group (if not present) =="
if ! id -u $APP_USER >/dev/null 2>&1; then
    sudo useradd -r -s /bin/false $APP_USER
fi

echo "== Copying application files =="
sudo cp -r lnmt/* /usr/local/lib/lnmt/
sudo cp lnmt-runner.py /usr/local/bin/lnmt-web
sudo chmod +x /usr/local/bin/lnmt-web

echo "== Creating initial config if not present =="
sudo cp default_server_config.json /etc/lnmt/server_config.json 2>/dev/null || true

echo "== Setting up systemd service =="
sudo cp lnmt.service /etc/systemd/system/lnmt.service
sudo systemctl daemon-reload
sudo systemctl enable lnmt.service

echo "== Setting permissions =="
sudo chown -R $APP_USER:$APP_GROUP /etc/lnmt
sudo chown -R $APP_USER:$APP_GROUP /usr/local/lib/lnmt

echo "== Done! Use: sudo systemctl start lnmt =="
