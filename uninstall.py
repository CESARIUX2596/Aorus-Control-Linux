#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import subprocess
import sys

if os.geteuid()!=0:
    sys.exit("Run ./uninstall.sh")
subprocess.run(["systemctl","disable","--now","aorus-lighting-restore.service"],check=False)
for name in [
    "/etc/systemd/system/aorus-lighting-restore.service",
    "/etc/systemd/user/aorus-lighting.service",
    "/usr/lib/systemd/system-sleep/aorus-lighting",
    "/etc/sudoers.d/aorus-lighting",
    "/etc/udev/rules.d/70-aorus-lighting.rules",
    "/etc/tmpfiles.d/aorus-lighting.conf",
    "/usr/local/sbin/aorus-lighting-boot",
    "/usr/local/share/applications/aorus-lighting.desktop",
    "/usr/local/share/icons/hicolor/scalable/apps/aorus-lighting.svg",
]:
    Path(name).unlink(missing_ok=True)
shutil.rmtree("/usr/local/lib/aorus-lighting",ignore_errors=True)
subprocess.run(["systemctl","daemon-reload"],check=True)
subprocess.run(["udevadm","control","--reload-rules"],check=True)
print("The boot profile in /var/lib/aorus-lighting was retained for reinstallation.")
