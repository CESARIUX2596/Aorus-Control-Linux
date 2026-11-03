#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "$(id -u)" = 0 ]; then
    echo 'Run ./install.sh as your desktop user, without sudo.' >&2
    exit 1
fi
command -v python3 >/dev/null
command -v sudo >/dev/null
command -v systemctl >/dev/null
echo 'Installing Lumen: local web interface, keyboard access, boot and resume restore.'
sudo /usr/bin/python3 "$project_dir/install.py" --user "$(id -un)"
systemctl --user daemon-reload
systemctl --user enable --now aorus-lighting.service
systemctl --user restart aorus-lighting.service
echo 'Ready: http://127.0.0.1:8765 — or open Lumen Keyboard from your app menu.'
