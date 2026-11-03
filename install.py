#!/usr/bin/env python3
"""Install trusted code and narrow boot/device integration. Run via install.sh."""
import argparse
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys

from model import DEFAULT

SOURCE = Path(__file__).resolve().parent
DEST = Path("/usr/local/lib/aorus-lighting")

def write(path, data, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"Refusing symlink: {path}")
    path.write_text(data)
    path.chmod(mode)
    os.chown(path,0,0)

def install(user):
    if os.geteuid()!=0:
        raise ValueError("Run ./install.sh as your regular desktop user.")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]*\$?",user):
        raise ValueError("Invalid desktop username")
    account = pwd.getpwnam(user)
    if account.pw_uid==0:
        raise ValueError("Choose a regular desktop user, not root.")
    # Never serve new assets using an older process's imported layout/model.
    runtime = Path(f"/run/user/{account.pw_uid}")
    if (runtime/"bus").exists() and Path("/etc/systemd/user/aorus-lighting.service").exists():
        stop = subprocess.run([
            shutil.which("runuser") or "/usr/sbin/runuser", "--user", user, "--",
            "/usr/bin/env", f"XDG_RUNTIME_DIR={runtime}", f"DBUS_SESSION_BUS_ADDRESS=unix:path={runtime}/bus",
            "/usr/bin/systemctl", "--user", "stop", "aorus-lighting.service",
        ],capture_output=True,text=True,timeout=15)
        if stop.returncode:
            raise ValueError("Could not stop the previous app before upgrading: "+stop.stderr.strip())
    DEST.mkdir(parents=True,exist_ok=True)
    for name in ["model.py","hardware.py","server.py","boot.py","launch.py"]:
        write(DEST/name,(SOURCE/name).read_text())
    for name in ["index.html","style.css","app.js","icon.svg"]:
        write(DEST/"static"/name,(SOURCE/"static"/name).read_text())
    write("/usr/local/sbin/aorus-lighting-boot",'''#!/usr/bin/python3 -I
import os, sys
sys.path.insert(0,"/usr/local/lib/aorus-lighting")
import boot
if os.geteuid() != 0 or sys.argv[1:] != ["save"]:
    sys.exit("Only the save operation is supported")
try:
    boot.save()
except (OSError, ValueError, KeyError, TypeError) as exc:
    sys.exit(str(exc))
''',0o755)
    sudoers = f"{user} ALL=(root) NOPASSWD: /usr/local/sbin/aorus-lighting-boot save\n"
    check = subprocess.run(["visudo","-cf","-"],input=sudoers,text=True,capture_output=True)
    if check.returncode:
        raise ValueError("Could not validate the restricted boot helper rule: "+check.stderr)
    write("/etc/sudoers.d/aorus-lighting",sudoers,0o440)
    write("/etc/udev/rules.d/70-aorus-lighting.rules",'''# Match the USB device, then its lighting interface in separate parent matches.
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1044", ATTRS{idProduct}=="7a3f", ENV{LUMEN_KEYBOARD}="1"
SUBSYSTEM=="hidraw", ENV{LUMEN_KEYBOARD}=="1", ATTRS{bInterfaceNumber}=="03", MODE="0660", TAG+="uaccess"
''')
    write("/etc/tmpfiles.d/aorus-lighting.conf","f /run/lock/aorus-lighting.lock 0644 root root -\n")
    write("/etc/systemd/system/aorus-lighting-restore.service",'''[Unit]
Description=Restore Lumen AORUS keyboard lighting
After=systemd-udev-trigger.service systemd-tmpfiles-setup.service
Before=display-manager.service
ConditionPathExists=/var/lib/aorus-lighting/startup.json

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -I /usr/local/lib/aorus-lighting/boot.py restore
TimeoutStartSec=20
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
RestrictAddressFamilies=AF_UNIX

[Install]
WantedBy=multi-user.target
''')
    write("/usr/lib/systemd/system-sleep/aorus-lighting",'''#!/bin/sh
if [ "$1" = post ]; then
    /usr/bin/systemctl --no-block start aorus-lighting-restore.service
fi
''',0o755)
    write("/etc/systemd/user/aorus-lighting.service",'''[Unit]
Description=Lumen local keyboard lighting studio
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/lib/aorus-lighting/server.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
''')
    write("/usr/local/share/applications/aorus-lighting.desktop",'''[Desktop Entry]
Type=Application
Name=Lumen Keyboard
Comment=Local AORUS keyboard lighting studio
Exec=/usr/bin/python3 /usr/local/lib/aorus-lighting/launch.py
Icon=aorus-lighting
Terminal=false
Categories=Settings;HardwareSettings;
Keywords=AORUS;RGB;Keyboard;Lighting;Lumen;
''')
    write("/usr/local/share/icons/hicolor/scalable/apps/aorus-lighting.svg",(SOURCE/"static/icon.svg").read_text())
    startup = Path("/var/lib/aorus-lighting/startup.json")
    if not startup.exists():
        write(startup,json.dumps({"version":1,"enabled":True,"name":"Aurora","config":DEFAULT},indent=2)+"\n")
    for cmd in [
        ["systemd-tmpfiles","--create","/etc/tmpfiles.d/aorus-lighting.conf"],
        ["udevadm","control","--reload-rules"],
        ["udevadm","trigger","--subsystem-match=hidraw","--action=change"],
        ["udevadm","settle"],
        ["systemctl","daemon-reload"],
        ["systemctl","enable","aorus-lighting-restore.service"],
        ["systemctl","start","aorus-lighting-restore.service"],
    ]:
        subprocess.run(cmd,check=True,timeout=30)
    print("System integration installed. Default lighting is restored before sign-in and after sleep.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user",required=True)
    args = parser.parse_args()
    try:
        install(args.user)
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        sys.exit(str(exc))
