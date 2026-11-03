"""Narrow, native hidraw transport. Never detaches the typing driver."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import select
import struct
import sys
import time

from model import EFFECTS, nearest_palette, normalize, packet, payload

EXPECTED_DESCRIPTOR = bytes.fromhex("0601ff0901a101150026ff0075089540092081020921910209229508b102c0")

def discover():
    for item in sorted(Path("/sys/class/hidraw").glob("hidraw*")):
        try:
            info = dict(line.split("=",1) for line in (item/"device/uevent").read_text().splitlines() if "=" in line)
            if info.get("HID_ID") != "0003:00001044:00007A3F":
                continue
            if (item/"device/report_descriptor").read_bytes() != EXPECTED_DESCRIPTOR:
                continue
            return str(Path("/dev")/item.name)
        except OSError:
            continue
    return None

def status():
    path = discover()
    accessible = bool(path and os.access(path,os.R_OK|os.W_OK))
    return {"connected": path is not None, "accessible": accessible, "path": path, "name": "AORUS 15P RGB Keyboard", "usb_id": "1044:7a3f", "onboard_flash": False}

class HidTransport:
    def __init__(self,path):
        self.fd = os.open(path,os.O_RDWR|os.O_NONBLOCK|os.O_CLOEXEC)
        try:
            info = bytearray(8)
            fcntl.ioctl(self.fd,0x80084803,info,True)
            bus,vid,pid = struct.unpack("Ihh",info)
            if bus != 3 or vid & 65535 != 0x1044 or pid & 65535 != 0x7a3f:
                raise ValueError("The selected device is not this AORUS keyboard.")
            desc = bytearray(struct.pack("I",31)+bytes(4096))
            fcntl.ioctl(self.fd,0x90044802,desc,True)
            if desc[4:35] != EXPECTED_DESCRIPTOR:
                raise ValueError("The device is not the lighting interface.")
        except BaseException:
            self.close()
            raise

    def feature(self,data):
        result = fcntl.ioctl(self.fd,(3<<30)|(len(data)<<16)|(ord("H")<<8)|6,bytearray(data),True)
        if result != len(data):
            raise OSError(f"Incomplete feature report ({result}/{len(data)} bytes).")
        time.sleep(.065)

    def output(self,data):
        _,ready,_ = select.select([], [self.fd], [], 1.5)
        if not ready:
            raise TimeoutError("The keyboard did not accept the lighting data in time.")
        if os.write(self.fd,data) != len(data):
            raise OSError("Incomplete color report.")
        time.sleep(.100)

    def close(self):
        os.close(self.fd)

def write_config(transport, config):
    config = normalize(config)
    brightness = round(config["brightness"]/2)
    if config["effect"] == "custom":
        # Vendor slot 1 maps to custom effect 0x34. Eight payload reports.
        transport.feature(packet(0x12,1,8))
        data = payload(config)
        for start in range(0,512,64):
            transport.output(b"\x00"+data[start:start+64])
        transport.feature(packet(0x08,0x34,5,brightness,2,1))
    else:
        transport.feature(packet(0x08,0x33,5,50,2,1))
        transport.feature(packet(0x08,EFFECTS[config["effect"]]["mode"],config["speed"],brightness,nearest_palette(config["colors"][0]),0))

def apply(config):
    config = normalize(config)
    path = discover()
    if not path or not Path(path).exists():
        raise OSError("The keyboard lighting device is unavailable. Open the app from your desktop session.")
    # Same lock for the user's app and the system boot/resume restorer.
    lockpath = Path("/run/lock/aorus-lighting.lock")
    if lockpath.exists():
        lock = os.open(lockpath,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    else:
        # Development before installation: only this user's workers compete.
        lock = os.open(Path.home()/".cache/aorus-lighting.lock",os.O_CREAT|os.O_RDWR|os.O_CLOEXEC,0o600)
    try:
        deadline = time.monotonic()+3
        while True:
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic()>deadline:
                    raise TimeoutError("The keyboard is busy. Try again in a moment.")
                time.sleep(.05)
        transport = HidTransport(path)
        try:
            write_config(transport,config)
        finally:
            transport.close()
    finally:
        os.close(lock)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--status",action="store_true")
    args = parser.parse_args()
    try:
        if args.status:
            result = status()
        else:
            apply(json.loads(sys.stdin.read(16385)))
            result = {"ok":True}
        print(json.dumps(result))
    except (OSError,ValueError,TimeoutError) as exc:
        print(json.dumps({"ok":False,"error":str(exc)}))
        sys.exit(1)
