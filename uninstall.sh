#!/bin/sh
set -eu
if [ "$(id -u)" = 0 ]; then
    echo 'Run ./uninstall.sh as your desktop user, without sudo.' >&2
    exit 1
fi
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
echo 'Removing Lumen services and installed files. Your profile library will be kept.'
systemctl --user disable --now aorus-lighting.service || true
sudo /usr/bin/python3 "$project_dir/uninstall.py"
systemctl --user daemon-reload
echo 'Lumen removed. Saved profiles remain in ~/.config/aorus-lighting/.'
