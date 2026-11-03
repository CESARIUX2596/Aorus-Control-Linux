#!/usr/bin/env python3
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
import json

URL = "http://127.0.0.1:8765"

def ready():
    try:
        with urlopen(URL+"/api/health",timeout=.5) as response:
            return json.load(response).get("app")=="aorus-lumen"
    except (OSError,ValueError):
        return False

if not ready():
    started = subprocess.run(["systemctl","--user","start","aorus-lighting.service"],capture_output=True,timeout=8)
    if started.returncode:
        log = Path.home()/".cache/aorus-lighting.log"
        log.parent.mkdir(exist_ok=True,parents=True)
        with log.open("a") as out:
            subprocess.Popen([sys.executable,str(Path(__file__).resolve().parent/"server.py")],stdout=out,stderr=out,start_new_session=True)
    for _ in range(40):
        if ready():
            break
        time.sleep(.15)
if not ready():
    sys.exit("Could not start Lumen. Check ~/.cache/aorus-lighting.log.")
subprocess.run(["xdg-open",URL],check=False)
