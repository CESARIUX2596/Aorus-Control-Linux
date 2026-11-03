#!/usr/bin/env python3
"""Root-owned boot helper; validates data and only touches the lighting device."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time

# The installed service runs Python in isolated mode, using only root-owned code.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from model import checked_name, normalize

TARGET = Path("/var/lib/aorus-lighting/startup.json")

def save():
    raw = sys.stdin.buffer.read(16385)
    if len(raw)>16384:
        raise ValueError("Profile exceeds the size limit")
    value = json.loads(raw)
    if not isinstance(value,dict) or type(value.get("enabled")) is not bool:
        raise ValueError("Invalid startup profile")
    data = {"version":1,"enabled":value["enabled"],"name":checked_name(value.get("name")),"config":normalize(value.get("config"))}
    TARGET.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="startup.",suffix=".tmp",dir=TARGET.parent)
    temp = Path(temp_name)
    try:
        os.fchmod(fd,0o644)
        with os.fdopen(fd,"w") as f:
            json.dump(data,f,indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp,TARGET)
    finally:
        temp.unlink(missing_ok=True)
    print(json.dumps({"ok":True}))

def restore():
    if not TARGET.exists():
        return
    data = json.loads(TARGET.read_text())
    if data.get("enabled") is not True:
        return
    config = normalize(data["config"])
    from hardware import apply, discover
    deadline = time.monotonic()+15
    while not discover():
        if time.monotonic()>deadline:
            raise OSError("AORUS lighting interface was not found at boot")
        time.sleep(.5)
    apply(config)
    print("Lumen restored the saved keyboard lighting.")

if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["save"] and os.geteuid()==0:
            save()
        elif sys.argv[1:] == ["restore"]:
            restore()
        else:
            raise ValueError("Expected save or restore")
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)
