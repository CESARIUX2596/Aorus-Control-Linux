import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hardware
from model import DEFAULT, LAYOUT, SLOTS, TEMPLATES, nearest_palette, normalize, packet, payload, render_colors, rgb
from server import App, Handler, ThreadingHTTPServer

class ProtocolTests(unittest.TestCase):
    def test_vendor_header_vectors(self):
        # Known 8-byte wire headers plus the unnumbered HID report placeholder.
        self.assertEqual(packet(8,1,5,50,1,0).hex(),"0008000105320100be")
        self.assertEqual(packet(0x12,1,8).hex(),"0012000108000000e4")
        self.assertEqual(packet(8,0x34,5,50,2,1).hex(),"000800340532020189")

    def test_per_key_payload_matches_vendor_rgb_order(self):
        config = {**DEFAULT,"pattern":"solid","colors":["#000000"]*3,"overrides":{"14":"#ff2847"}}
        data = payload(config)
        self.assertEqual(len(data),512)
        self.assertEqual(data[56:60],bytes.fromhex("00ff2847"))
        self.assertEqual(data[:56],bytes(56))
        self.assertEqual(data[60:],bytes(452))

    def test_custom_upload_has_eight_paced_output_reports_and_commit(self):
        class Capture:
            def __init__(self): self.reports=[]
            def feature(self,data): self.reports.append(("feature",data))
            def output(self,data): self.reports.append(("output",data))
        transport=Capture()
        hardware.write_config(transport,{**DEFAULT,"brightness":100})
        self.assertEqual(transport.reports[0],("feature",bytes.fromhex("0012000108000000e4")))
        self.assertEqual([kind for kind,_ in transport.reports],["feature"]+["output"]*8+["feature"])
        self.assertTrue(all(len(data)==65 and data[0]==0 for _,data in transport.reports[1:9]))
        self.assertEqual(transport.reports[-1],("feature",bytes.fromhex("000800340532020189")))

    def test_model_rejects_unsupported_and_unbounded_data(self):
        for change in [{"effect":"wave"},{"brightness":101},{"brightness":True},{"speed":0},{"colors":["red"]*3},{"overrides":{"128":"#ffffff"}},{"overrides":{"../1":"#ffffff"}},{"overrides":{"14":"<script>"}}]:
            with self.subTest(change=change),self.assertRaises(ValueError): normalize({**DEFAULT,**change})

    def test_us_layout_matches_recovered_vendor_slots(self):
        self.assertEqual(len(SLOTS),128)
        for name,slot in {"esc":11,"a":14,"w":21,"y":45,"z":19,"slash":73,"space":42,"enter":92,"num_enter":114}.items():
            self.assertEqual(SLOTS.index(name),slot)
        self.assertEqual(len({k["slot"] for row in LAYOUT for k in row}),sum(len(row) for row in LAYOUT))

    def test_firmware_palette_uses_purple_at_six_and_green_at_four(self):
        self.assertEqual(nearest_palette("#bc4fff"),6)
        self.assertEqual(nearest_palette("#20ed74"),4)

    def test_gaming_movement_stands_out_from_background_and_function_keys(self):
        for theme in (t for t in TEMPLATES if t["config"]["pattern"]=="wasd"):
            with self.subTest(theme=theme["id"]):
                colors=render_colors(theme["config"])
                bright=max(rgb(colors[SLOTS.index("w")]))
                for name in ("h","j","f1","f12"):
                    self.assertGreaterEqual(bright, max(1,max(rgb(colors[SLOTS.index(name)])))*15)
                self.assertEqual(colors[SLOTS.index("w")],colors[SLOTS.index("left")])

    def test_background_glow_changes_only_the_non_action_keys(self):
        config=next(t["config"] for t in TEMPLATES if t["id"]=="gamer")
        dark=render_colors({**config,"background":0})
        light=render_colors({**config,"background":40})
        self.assertEqual(dark[SLOTS.index("h")],"#000000")
        self.assertNotEqual(dark[SLOTS.index("h")],light[SLOTS.index("h")])
        for name in ("w","a","s","d","left","q","space"):
            self.assertEqual(dark[SLOTS.index(name)],light[SLOTS.index(name)])

    def test_moba_uses_spell_keys_and_distinct_action_colors(self):
        config=next(t["config"] for t in TEMPLATES if t["id"]=="moba")
        colors=render_colors(config)
        for name in "qwer":self.assertEqual(colors[SLOTS.index(name)],config["colors"][1])
        self.assertNotEqual(colors[SLOTS.index("q")],colors[SLOTS.index("d")])
        self.assertGreater(max(rgb(colors[SLOTS.index("d")])),max(rgb(colors[SLOTS.index("h")]))*15)

    def test_scattered_texture_is_not_a_flat_matrix_column(self):
        config=next(t["config"] for t in TEMPLATES if t["id"]=="matrix")
        colors=render_colors(config)
        self.assertGreater(len({colors[slot] for slot in (14,15,16,17)}),1)

    def test_thirty_presets_have_distinct_outputs_and_valid_reports(self):
        self.assertEqual(len(TEMPLATES),30)
        self.assertEqual(len({t["id"] for t in TEMPLATES}),30)
        signatures=set()
        for theme in TEMPLATES:
            config=normalize(theme["config"])
            data=payload(config)
            self.assertEqual(len(data),512)
            signatures.add((config["effect"],hashlib.sha256(data).hexdigest()))
        self.assertEqual(len(signatures),30)

    def test_old_profiles_gain_background_default_without_losing_paint(self):
        old={**DEFAULT,"overrides":{"14":"#ff0000"}}
        old.pop("background")
        restored=normalize(old)
        self.assertEqual(restored["background"],8)
        self.assertEqual(restored["overrides"],{"14":"#ff0000"})
        for invalid in (-1,41,True,"8"):
            with self.assertRaises(ValueError):normalize({**old,"background":invalid})

    def test_ansi_geometry_matches_confirmed_aorus_15p_reference(self):
        keys={k["id"]:k for row in LAYOUT for k in row}
        self.assertEqual([k["id"] for k in LAYOUT[0]], ["esc"]+[f"f{i}" for i in range(1,13)]+["pause","delete","home","pageup","pagedown","end"])
        self.assertEqual(keys["enter"]["height"],1)
        self.assertEqual(keys["enter"]["width"],2.25)
        self.assertEqual((keys["num_plus"]["y"],keys["num_plus"]["height"]),(2,2))
        self.assertEqual((keys["num_enter"]["y"],keys["num_enter"]["height"]),(4,2))
        self.assertEqual(keys["up"]["x"],keys["down"]["x"])
        self.assertEqual(keys["right"]["x"],keys["num1"]["x"])
        self.assertEqual(keys["num0"]["width"],1)
        occupied=set()
        for key in keys.values():
            left=round((key["x"]-key["width"]/2)*4)
            for row in range(key["y"],key["y"]+key["height"]):
                for column in range(left,left+round(key["width"]*4)):
                    self.assertNotIn((column,row),occupied)
                    occupied.add((column,row))
        self.assertEqual(occupied,{(column,row) for column in range(76) for row in range(6)})

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.app=App(Path(cls.temp.name),demo=True)
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        cls.server.app=cls.app
        cls.url=f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()

    def request(self,path,data=None,headers=None):
        headers={"Content-Type":"application/json","X-Lumen-Token":self.app.token,**(headers or {})}
        request=Request(self.url+path,data=None if data is None else json.dumps(data).encode(),headers=headers)
        with urlopen(request,timeout=5) as response:
            return response.status,response.headers,response.read()

    def test_assets_and_live_state(self):
        for path,mime in [("/","text/html"),("/app.js","text/javascript"),("/style.css","text/css"),("/icon.svg","image/svg+xml")]:
            status,headers,body=self.request(path)
            self.assertEqual(status,200);self.assertTrue(headers["Content-Type"].startswith(mime));self.assertGreater(len(body),100)
            self.assertIn("frame-ancestors 'none'",headers["Content-Security-Policy"])
        state=json.loads(self.request("/api/state")[2]);self.assertTrue(state["demo"]);self.assertEqual(len(state["templates"]),30)

    def test_theme_cards_and_saved_profiles_use_exact_device_colors(self):
        state=json.loads(self.request("/api/state")[2])
        for template in state["templates"]:
            colors=json.loads(self.request("/api/preview",{"config":template["config"]})[2])["colors"]
            self.assertEqual(colors,template["preview"])
        config={**DEFAULT,"pattern":"wasd","background":0,"overrides":{"14":"#f02690"}}
        saved=json.loads(self.request("/api/profiles/save",{"name":"Preview parity","config":config})[2])["profile"]
        self.assertEqual(saved["preview"],render_colors(config))
        self.assertEqual(saved["preview"][14],"#f02690")
        self.request("/api/profiles/delete",{"id":saved["id"]})

    def test_profile_library_survives_server_restart(self):
        name='<img src=x onerror=alert(1)>'
        result=json.loads(self.request("/api/profiles/save",{"name":name,"config":DEFAULT})[2])
        restored=App(Path(self.temp.name),demo=True)
        self.assertTrue(any(p["name"]==name for p in restored.profiles))
        self.request("/api/profiles/delete",{"id":result["profile"]["id"]})
        self.assertFalse(any(p["name"]==name for p in App(Path(self.temp.name),demo=True).profiles))

    def test_boot_profile_restore_state_and_disable(self):
        result=json.loads(self.request("/api/save-to-keyboard",{"name":"Aurora","config":DEFAULT})[2])
        self.assertTrue(result["remembered"]);self.assertTrue(result["startup"]["enabled"])
        self.assertEqual(App(Path(self.temp.name),demo=True).boot_state()["config"],normalize(DEFAULT))
        self.request("/api/remember",{"enabled":False,"name":"Aurora","config":DEFAULT})
        self.assertFalse(App(Path(self.temp.name),demo=True).boot_state()["enabled"])

    def test_rejects_cross_origin_and_missing_token(self):
        for headers in [{"Origin":"https://example.com"},{"Host":"attacker.invalid"},{"X-Lumen-Token":""},{"Sec-Fetch-Site":"cross-site"}]:
            with self.subTest(headers=headers),self.assertRaises(HTTPError) as ctx:
                self.request("/api/apply",{"config":DEFAULT},headers)
            self.assertEqual(ctx.exception.code,403)
            ctx.exception.close()

    def test_invalid_config_does_not_touch_active_lighting(self):
        previous=copy.deepcopy(self.app.active)
        with self.assertRaises(HTTPError) as ctx:
            self.request("/api/apply",{"config":{**DEFAULT,"brightness":-1}})
        self.assertEqual(ctx.exception.code,400);self.assertEqual(self.app.active,previous)
        ctx.exception.close()

    def test_path_traversal_is_not_served(self):
        with self.assertRaises(HTTPError) as ctx:
            self.request("/../server.py")
        self.assertEqual(ctx.exception.code,404)
        ctx.exception.close()

    def test_link_from_another_app_can_open_the_document(self):
        status,_,_=self.request("/",headers={"Sec-Fetch-Site":"cross-site","Sec-Fetch-Mode":"navigate"})
        self.assertEqual(status,200)

    def test_cross_site_navigation_cannot_read_api_state(self):
        with self.assertRaises(HTTPError) as ctx:
            self.request("/api/state",headers={"Sec-Fetch-Site":"cross-site","Sec-Fetch-Mode":"navigate"})
        self.assertEqual(ctx.exception.code,403)
        ctx.exception.close()

if __name__=="__main__": unittest.main()
