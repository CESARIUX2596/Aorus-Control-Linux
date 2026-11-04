#!/usr/bin/env python3
"""Lumen: a loopback-only, dependency-free keyboard lighting application."""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
import uuid

import hardware
import system_controls
from model import APP_VERSION, DEFAULT, EFFECTS, LAYOUT, PALETTE, TEMPLATES, checked_name, normalize, render_colors

ROOT = Path(__file__).resolve().parent
BOOT_FILE = Path("/var/lib/aorus-lighting/startup.json")
BOOT_HELPER = Path("/usr/local/sbin/aorus-lighting-boot")

def atomic_json(path, value, mode=0o600):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp = path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    try:
        fd = os.open(temp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,mode)
        with os.fdopen(fd,"w") as f:
            json.dump(value,f,indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        temp.unlink(missing_ok=True)

class App:
    def __init__(self, directory, demo=False):
        self.directory = directory
        self.demo = demo
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.active = None
        self.last_applied = None
        self.profiles = []
        self.boot = {"enabled": False, "name": "No startup profile", "config": None}
        try:
            data = json.loads((directory/"profiles.json").read_text())
            for entry in data.get("profiles",[])[:50]:
                self.profiles.append({"id":str(uuid.UUID(entry["id"])), "name":checked_name(entry["name"]), "config":normalize(entry["config"])})
        except (OSError,ValueError,KeyError,TypeError):
            pass

    def boot_state(self):
        source = self.directory/"demo-startup.json" if self.demo else BOOT_FILE
        try:
            data = json.loads(source.read_text())
            self.boot = {"enabled":data.get("enabled") is True,"name":checked_name(data["name"]),"config":normalize(data["config"])}
        except (OSError,ValueError,KeyError,TypeError):
            pass
        return {**self.boot,"installed":self.demo or BOOT_HELPER.exists(),"onboard_flash":False}

    def state(self):
        with self.lock:
            device = hardware.status()
            if self.demo:
                device.update(connected=False,accessible=False,name="Interface preview — no hardware writes")
            return {"app":"aorus-lumen","version":APP_VERSION,"token":self.token,"demo":self.demo,"device":device,"system":system_controls.snapshot(),"templates":[self.preview_entry(t) for t in TEMPLATES],"layout":LAYOUT,"effects":EFFECTS,"palette":PALETTE,"profiles":[self.preview_entry(p) for p in self.profiles],"startup":self.boot_state(),"active":self.active,"last_applied":self.last_applied,"default":DEFAULT}

    @staticmethod
    def preview_entry(entry):
        return {**entry,"preview":render_colors(entry["config"])}

    def apply(self, config):
        config = normalize(config)
        with self.lock:
            if not self.demo:
                try:
                    completed = subprocess.run([sys.executable,str(ROOT/"hardware.py")],input=json.dumps(config),capture_output=True,text=True,timeout=8)
                except subprocess.TimeoutExpired:
                    raise ValueError("The keyboard operation timed out. No automatic retries were sent.")
                try:
                    result = json.loads(completed.stdout)
                except (ValueError,TypeError):
                    raise ValueError("The controller could not complete the lighting change.")
                if completed.returncode or not result.get("ok"):
                    raise ValueError(result.get("error","Could not apply the lighting."))
            self.active = config
            self.last_applied = datetime.now(timezone.utc).isoformat()
            return {"ok":True,"demo":self.demo,"config":config,"message":"Preview updated; no keyboard was changed." if self.demo else "Lighting applied to your keyboard."}

    def remember(self, config, name, enabled):
        config = normalize(config)
        name = checked_name(name)
        data = {"enabled":enabled is True,"name":name,"config":config,"version":1}
        if self.demo:
            atomic_json(self.directory/"demo-startup.json",data)
        else:
            if not BOOT_HELPER.exists():
                raise ValueError("Run the one-time installer to enable automatic boot lighting.")
            result = subprocess.run(["sudo","-n",str(BOOT_HELPER),"save"],input=json.dumps(data),capture_output=True,text=True,timeout=5)
            if result.returncode:
                detail = result.stderr.strip()[:600] or f"Helper exited with code {result.returncode}."
                print("Boot-profile save failed: "+detail,file=sys.stderr,flush=True)
                raise ValueError("Could not save the boot profile. "+detail)
        self.boot = data
        return {"ok":True,"startup":self.boot_state()}

    def action(self, route, data):
        if not isinstance(data,dict):
            raise ValueError("Expected a JSON object.")
        with self.lock:
            if route == "/api/system/action":
                name, value = data.get("name"), data.get("value")
                if not isinstance(name, str) or not isinstance(value, str):
                    raise ValueError("Choose a supported laptop action.")
                return system_controls.action(name, value, self.demo)
            if route == "/api/preview":
                config = normalize(data.get("config"))
                return {"colors":render_colors(config),"config":config}
            if route == "/api/apply":
                return self.apply(data.get("config"))
            if route == "/api/remember":
                return self.remember(data.get("config"),data.get("name"),data.get("enabled",True))
            if route == "/api/save-to-keyboard":
                config = normalize(data.get("config"))
                checked_name(data.get("name"))
                result = self.apply(config)
                try:
                    result.update(self.remember(config,data["name"],True))
                except (ValueError,subprocess.TimeoutExpired) as exc:
                    return {**result,"remembered":False,"message":"Applied to keyboard, but the boot profile could not be saved. "+str(exc)}
                return {**result,"remembered":True,"message":"Preview startup saved." if self.demo else "Applied to keyboard and saved for automatic boot restore."}
            if route == "/api/profiles/save":
                name = checked_name(data.get("name"))
                config = normalize(data.get("config"))
                if len(self.profiles)>=50:
                    raise ValueError("Your library is full. Delete a profile before adding another.")
                entry = {"id":str(uuid.uuid4()),"name":name,"config":config}
                profiles = [*self.profiles,entry]
                atomic_json(self.directory/"profiles.json",{"version":1,"profiles":profiles})
                self.profiles = profiles
                return {"ok":True,"profile":self.preview_entry(entry),"profiles":[self.preview_entry(p) for p in self.profiles]}
            if route == "/api/profiles/delete":
                id = data.get("id")
                if not any(p["id"]==id for p in self.profiles):
                    raise ValueError("That profile no longer exists.")
                profiles = [p for p in self.profiles if p["id"]!=id]
                atomic_json(self.directory/"profiles.json",{"version":1,"profiles":profiles})
                self.profiles = profiles
                return {"ok":True,"profiles":[self.preview_entry(p) for p in profiles]}
            raise KeyError("Unknown action.")

class Handler(BaseHTTPRequestHandler):
    server_version = "Lumen/1.2"

    def log_message(self,fmt,*args):
        if args and str(args[1:2]) != "('200',)":
            super().log_message(fmt,*args)

    def trusted(self):
        port = self.server.server_address[1]
        host = self.headers.get("Host","")
        allowed = {f"127.0.0.1:{port}",f"localhost:{port}"}
        cross_site = self.headers.get("Sec-Fetch-Site","") == "cross-site"
        # A link from another app may open the document; API requests still
        # require the correct origin and mutation token.
        document_navigation = self.command == "GET" and urlsplit(self.path).path == "/" and self.headers.get("Sec-Fetch-Mode") == "navigate"
        return host in allowed and self.headers.get("Origin",f"http://{host}") == f"http://{host}" and (not cross_site or document_navigation)

    def respond(self,status,data,mime="application/json; charset=utf-8"):
        body = json.dumps(data).encode() if mime.startswith("application/json") else data
        self.send_response(status)
        self.send_header("Content-Type",mime)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.trusted():
            return self.respond(403,{"error":"Open Lumen using its local address."})
        route = urlsplit(self.path).path
        if route == "/api/health":
            return self.respond(200,{"app":"aorus-lumen","ok":True})
        if route == "/api/state":
            return self.respond(200,self.server.app.state())
        if route == "/api/system":
            return self.respond(200,system_controls.snapshot())
        assets = {"/":("index.html","text/html; charset=utf-8"),"/style.css":("style.css","text/css; charset=utf-8"),"/system.css":("system.css","text/css; charset=utf-8"),"/app.js":("app.js","text/javascript; charset=utf-8"),"/icon.svg":("icon.svg","image/svg+xml")}
        if route not in assets:
            return self.respond(404,{"error":"Not found."})
        name,mime = assets[route]
        self.respond(200,(ROOT/"static"/name).read_bytes(),mime)

    def do_POST(self):
        if not self.trusted() or not secrets.compare_digest(self.headers.get("X-Lumen-Token",""),self.server.app.token):
            return self.respond(403,{"error":"Refresh the page to reconnect to Lumen."})
        if self.headers.get_content_type() != "application/json":
            return self.respond(415,{"error":"Expected JSON."})
        try:
            size = int(self.headers.get("Content-Length","0"))
            if not 0 < size <= 16384:
                return self.respond(413,{"error":"Request is too large or empty."})
            self.connection.settimeout(12)
            data = json.loads(self.rfile.read(size))
            result = self.server.app.action(urlsplit(self.path).path,data)
            self.respond(200,result)
        except KeyError:
            self.respond(404,{"error":"Unknown action."})
        except (ValueError,TypeError) as exc:
            self.respond(400,{"error":str(exc)})
        except (OSError,subprocess.TimeoutExpired) as exc:
            self.respond(503,{"error":"The lighting service could not complete this operation. "+str(exc)})

def main():
    parser = argparse.ArgumentParser(description="Lumen local keyboard studio")
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--demo",action="store_true",help="Preview without touching the keyboard")
    parser.add_argument("--data-dir",type=Path,default=Path(os.environ.get("XDG_CONFIG_HOME",str(Path.home()/".config")))/"aorus-lighting")
    args = parser.parse_args()
    app = App(args.data_dir,args.demo)
    server = ThreadingHTTPServer(("127.0.0.1",args.port),Handler)
    server.daemon_threads = True
    server.app = app
    print(f"Lumen ready at http://127.0.0.1:{server.server_address[1]}",flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
