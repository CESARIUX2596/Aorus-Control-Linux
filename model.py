"""Profiles and the 1044:7a3f lighting model. No hardware access."""
import colorsys
import re

APP_VERSION = "1.2.2"

EFFECTS = {
    "custom": {"label": "Custom colors", "mode": 52},
    "static": {"label": "Solid glow", "mode": 1},
    "breathing": {"label": "Breathing", "mode": 2},
    "ripple": {"label": "Reactive ripple", "mode": 6},
    "neon": {"label": "Spectrum cycle", "mode": 8},
    "rainbow": {"label": "Rainbow marquee", "mode": 9},
    "raindrop": {"label": "Raindrop", "mode": 10},
    "rotate": {"label": "Color rotation", "mode": 13},
}
# This firmware's indexed palette is red/orange/yellow/green/blue/purple/white.
# Direct RGB uploads support cyan; indexed value 6 is purple, not cyan.
PALETTE = ["#ff2847", "#ff8c32", "#ffdc42", "#20ed74", "#325dff", "#bc4fff", "#ffffff"]
# Key slot mapping follows the Fusion controller's six-row matrix.
SLOTS = [
    "", "", "", "", "", "", "ctrl_l", "shift_l", "caps", "tab", "grave", "esc",
    "fn", "backslash", "a", "q", "1", "f1", "win", "z", "s", "w", "2", "f2",
    "alt_l", "x", "d", "e", "3", "f3", "", "c", "f", "r", "4", "f4",
    "", "v", "g", "t", "5", "f5", "space", "b", "h", "y", "6", "f6",
    "", "n", "j", "u", "7", "f7", "", "m", "k", "i", "8", "f8",
    "alt_r", "comma", "l", "o", "9", "f9", "menu", "period", "semicolon", "p", "0", "f10",
    "ctrl_r", "slash", "quote", "bracket_l", "equal", "f11", "", "", "", "bracket_r", "minus", "f12",
    "left", "shift_r", "iso_hash", "", "", "pause", "down", "up", "enter", "", "backspace", "delete",
    "right", "num1", "num4", "num7", "numlock", "home", "num0", "num2", "num5", "num8", "num_slash", "pageup",
    "num_dot", "num3", "num6", "num9", "num_star", "pagedown", "num_enter", "", "num_plus", "", "num_minus", "end",
    "", "", "", "", "", "", "", "",
]
ROW_DEFS = [
    [("esc", "esc", 1)] + [(f"f{i}", f"F{i}", 1) for i in range(1, 13)] + [("pause", "pause", 1), ("delete", "del", 1), ("home", "home", 1), ("pageup", "pg↑", 1), ("pagedown", "pg↓", 1), ("end", "end", 1)],
    [("grave", "`", 1)] + [(str(i), str(i), 1) for i in [1,2,3,4,5,6,7,8,9,0]] + [("minus", "−", 1), ("equal", "=", 1), ("backspace", "⌫", 2), ("numlock", "num", 1), ("num_slash", "/", 1), ("num_star", "*", 1), ("num_minus", "−", 1)],
    [("tab", "tab", 1.5)] + [(c,c.upper(),1) for c in "qwertyuiop"] + [("bracket_l", "[", 1), ("bracket_r", "]", 1), ("backslash", "\\", 1.5), ("num7", "7", 1), ("num8", "8", 1), ("num9", "9", 1), ("num_plus", "+", 1, 2)],
    [("caps", "caps", 1.75)] + [(c,c.upper(),1) for c in "asdfghjkl"] + [("semicolon", ";", 1), ("quote", "'", 1), ("enter", "enter", 2.25), ("num4", "4", 1), ("num5", "5", 1), ("num6", "6", 1)],
    [("shift_l", "shift", 2.25)] + [(c,c.upper(),1) for c in "zxcvbnm"] + [("comma", ",", 1), ("period", ".", 1), ("slash", "/", 1), ("shift_r", "shift", 1.75), ("up", "↑", 1), ("num1", "1", 1), ("num2", "2", 1), ("num3", "3", 1), ("num_enter", "↵", 1, 2)],
    [("ctrl_l", "ctrl", 1.25), ("fn", "fn", 1), ("win", "◇", 1), ("alt_l", "alt", 1), ("space", "", 5.5), ("alt_r", "alt", 1), ("menu", "☰", 1), ("ctrl_r", "ctrl", 1.25), ("left", "←", 1), ("down", "↓", 1), ("right", "→", 1), ("num0", "0", 1), ("num_dot", ".", 1)],
]
LAYOUT = []
for row_number, row in enumerate(ROW_DEFS):
    x = 0
    items = []
    for definition in row:
        key, label, width = definition[:3]
        height = definition[3] if len(definition)>3 else 1
        items.append({"id": key, "label": label, "slot": SLOTS.index(key), "width": width, "height": height, "x": x + width/2, "y": row_number})
        x += width
    LAYOUT.append(items)
POSITIONS = {k["slot"]: k for row in LAYOUT for k in row}

PATTERNS = ("gradient", "solid", "split", "spectrum", "wasd", "moba", "rows", "checker", "scatter")
GAMING_PATTERNS = ("wasd", "moba")
MOVEMENT = frozenset(("w", "a", "s", "d", "up", "down", "left", "right"))
ACTIONS = frozenset(("q", "e", "r", "f", "1", "2", "3", "4", "5", "shift_l", "ctrl_l", "space", "esc"))
MODIFIERS = frozenset(("esc", "tab", "caps", "ctrl_l", "ctrl_r", "shift_l", "shift_r", "alt_l", "alt_r", "win", "fn", "menu", "space", "enter", "backspace", "delete"))
DEFAULT = {"effect": "custom", "pattern": "gradient", "colors": ["#20edba", "#34b8ff", "#a76aff"], "brightness": 70, "speed": 5, "background": 8, "reverse": False, "overrides": {}}

def preset(id, name, description, colors, pattern="gradient", effect="custom", tag="Gradient", background=8):
    return {"id": id, "name": name, "description": description, "tag": tag, "config": {**DEFAULT, "colors": colors, "pattern": pattern, "effect": effect, "background": background, "overrides": {}}}

TEMPLATES = [
    preset("aurora", "Aurora", "Northern lights, right at your fingertips.", ["#20edba", "#34b8ff", "#a76aff"]),
    preset("synthwave", "Synthwave", "After-hours pink meets electric blue.", ["#ff3eaa", "#9d4dff", "#3b8bff"]),
    preset("sunset", "Golden hour", "A little warmth for your late-night ideas.", ["#ffcc62", "#ff704d", "#c24bba"]),
    preset("glacier", "Glacier", "Crisp ice blue. Quietly brilliant.", ["#c7f5ff", "#5ac8fa", "#4566f5"]),
    preset("ember", "Ember", "A slow burn of amber and deep red.", ["#ffbd45", "#ff6329", "#b31b37"]),
    preset("spectrum", "Prism", "The whole spectrum. Zero compromises.", ["#ff427e", "#5c65ff", "#2ce5ad"], "spectrum", tag="Pattern"),
    preset("gamer", "Night runner", "Neon mint movement keys, pink actions, and a barely-lit background.", ["#152445", "#00ff85", "#ff4fb7"], "wasd", tag="Gaming"),
    preset("focus", "Soft focus", "A warm, simple glow for getting in the zone.", ["#ffdba8", "#ffdba8", "#ffdba8"], "solid", tag="Solid"),
    preset("breathing", "Deep breath", "Let your keyboard take a breath.", ["#bc4fff", "#325dff", "#ff2847"], "solid", "breathing", "Animated"),
    preset("neon", "Color drift", "A continuous, onboard spectrum cycle.", ["#bc4fff", "#23dcea", "#ff2847"], "spectrum", "neon", "Animated"),
    preset("dracula", "Dracula", "Purple, pink, and green bands inspired by Dracula Classic.", ["#bd93f9", "#ff79c6", "#50fa7b"], "rows", tag="Palette"),
    preset("catppuccin", "Catppuccin", "Mocha's lavender, mauve, and peach as a soft pastel fade.", ["#b4befe", "#cba6f7", "#fab387"], tag="Palette"),
    preset("tokyo", "Tokyo night", "Storm blue, magenta, and cyan in three clean zones.", ["#7aa2f7", "#bb9af7", "#7dcfff"], "split", tag="Palette"),
    preset("nord", "Nord frost", "An icy fade through Nord's Frost blues and teal.", ["#5e81ac", "#88c0d0", "#8fbcbb"], tag="Palette"),
    preset("solarized", "Solarized", "Teal, golden yellow, and blue in deliberate blocks.", ["#2aa198", "#b58900", "#268bd2"], "split", tag="Palette"),
    preset("gruvbox", "Gruvbox", "Retro amber, orange, and green in horizontal bands.", ["#fabd2f", "#fe8019", "#b8bb26"], "rows", tag="Palette"),
    preset("rose-pine", "Rosé pine", "Rose, iris, and foam from the Rosé Pine palette.", ["#ebbcba", "#c4a7e7", "#9ccfd8"], "rows", tag="Palette"),
    preset("cyberpunk", "Cyberpunk", "Acid yellow, hot pink, and electric cyan. Loud on purpose.", ["#ffee00", "#ff007a", "#00f0ff"], "split", tag="Pattern"),
    preset("matrix", "Digital rain", "Scattered green lights on a nearly black keyboard. A static rain pattern.", ["#07350d", "#00ff41", "#c0ffca"], "scatter", tag="Pattern", background=3),
    preset("ocean", "Ocean current", "Saturated cobalt gives way to cyan and sea green.", ["#003dff", "#00dcff", "#00ff91"]),
    preset("miami", "Miami vice", "A cyan, pink, and gold trip down the coast.", ["#00e5ff", "#ff2f92", "#ffbd00"], "split", tag="Pattern"),
    preset("sakura", "Sakura", "Cherry-pink and pale-white checker keys, with lavender modifiers.", ["#ff6da8", "#fff0f7", "#c792ea"], "checker", tag="Pattern"),
    preset("lava", "Lava flow", "Deep red, molten scarlet, and bright amber rows.", ["#9f0505", "#ff2400", "#ff9a00"], "rows", tag="Pattern"),
    preset("toxic", "Toxic bloom", "Lime movement keys and magenta actions on a dark deck.", ["#152300", "#c5ff00", "#ff2084"], "wasd", tag="Gaming", background=5),
    preset("tactical", "FPS tactical", "Amber WASD and arrows; cyan reload, jump, and action keys.", ["#173342", "#ffb000", "#00e5ff"], "wasd", tag="Gaming", background=8),
    preset("moba", "Spellbook", "QWER spells shine purple; number keys and D/F glow cyan.", ["#251034", "#df23ff", "#00f0ff"], "moba", tag="Gaming", background=5),
    preset("redline", "Redline", "Red movement keys and white action keys against a dark background.", ["#2a0808", "#ff2020", "#ffffff"], "wasd", tag="Gaming", background=4),
    preset("noir", "Stealth ops", "Only movement and action keys are lit. Everything else stays off.", ["#101827", "#ffffff", "#4b8dff"], "wasd", tag="Gaming", background=0),
    preset("split-personality", "Pixel arcade", "Cyan and dark alternating keys, with hot-pink modifiers.", ["#010613", "#00c8ff", "#ff156c"], "checker", tag="Pattern"),
    preset("zen", "Zen garden", "Forest, fresh green, and pale-lime rows.", ["#10612c", "#43d65a", "#e6ff85"], "rows", tag="Pattern"),
]

def normalize(value):
    if not isinstance(value, dict):
        raise ValueError("Choose a valid lighting profile.")
    effect = value.get("effect", "custom")
    pattern = value.get("pattern", "gradient")
    if effect not in EFFECTS or pattern not in PATTERNS:
        raise ValueError("Unsupported lighting effect or pattern.")
    colors = value.get("colors", DEFAULT["colors"])
    if not isinstance(colors, list) or len(colors) != 3 or any(not isinstance(c,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in colors):
        raise ValueError("Use three colors in #RRGGBB format.")
    brightness = value.get("brightness", 70)
    speed = value.get("speed", 5)
    background = value.get("background", DEFAULT["background"])
    if type(brightness) is not int or not 0 <= brightness <= 100 or type(speed) is not int or not 1 <= speed <= 10:
        raise ValueError("Brightness must be 0–100 and speed 1–10.")
    if type(background) is not int or not 0 <= background <= 40:
        raise ValueError("Background glow must be 0–40%.")
    overrides = value.get("overrides", {})
    if not isinstance(overrides,dict) or len(overrides) > 128:
        raise ValueError("Invalid per-key colors.")
    for slot, color in overrides.items():
        if not isinstance(slot,str) or not slot.isdecimal() or str(int(slot)) != slot or int(slot) not in POSITIONS or not isinstance(color,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",color):
            raise ValueError("Invalid key or color.")
    return {"effect": effect, "pattern": pattern, "colors": [c.lower() for c in colors], "brightness": brightness, "speed": speed, "background": background, "reverse": value.get("reverse") is True, "overrides": {k:v.lower() for k,v in overrides.items()}}

def rgb(color):
    return tuple(int(color[i:i+2],16) for i in (1,3,5))

def hex_color(color):
    return "#" + "".join(f"{max(0,min(255,round(x))):02x}" for x in color)

def nearest_palette(color):
    c = rgb(color)
    return 1 + min(range(7), key=lambda i: sum((a-b)**2 for a,b in zip(c,rgb(PALETTE[i]))))

def scaled(color, amount):
    return tuple(c*amount for c in color)

def gaming_color(pattern, key, colors, background):
    if pattern == "wasd":
        if key in MOVEMENT:
            return colors[1]
        if key in ACTIONS:
            return scaled(colors[2],.55)
    else:
        if key in ("q","w","e","r"):
            return colors[1]
        if key in ("d","f","1","2","3","4","5","6"):
            return scaled(colors[2],.85)
        if key in ("a","s","space","shift_l","ctrl_l"):
            return scaled(colors[2],.4)
    return scaled(colors[0],background/100)

def render_colors(config):
    config = normalize(config)
    colors = [rgb(c) for c in config["colors"]]
    result = ["#000000"] * 128
    for slot, key in POSITIONS.items():
        t = max(0,min(1,key["x"]/19))
        if config["reverse"]:
            t = 1-t
        pattern = config["pattern"]
        if config["effect"] != "custom":
            color = rgb(PALETTE[nearest_palette(config["colors"][0])-1])
            if config["effect"] in ("neon", "rainbow", "rotate", "raindrop"):
                color = tuple(c*255 for c in colorsys.hsv_to_rgb(t*.85, .8, 1))
        elif pattern == "solid":
            color = colors[0]
        elif pattern == "spectrum":
            color = tuple(c*255 for c in colorsys.hsv_to_rgb(t*.88, .8, 1))
        elif pattern == "split":
            color = colors[min(2,int(t*3))]
        elif pattern in GAMING_PATTERNS:
            color = gaming_color(pattern,key["id"],colors,config["background"])
        elif pattern == "rows":
            color = colors[(2-int(key["y"]//2)) if config["reverse"] else int(key["y"]//2)]
        elif pattern == "checker":
            color = colors[2] if key["id"] in MODIFIERS else colors[(int(key["x"])+key["y"]+int(config["reverse"]))%2]
        elif pattern == "scatter":
            seed = 127-slot if config["reverse"] else slot
            phase = (((seed*1103515245+12345) ^ (key["y"]*2654435761))>>16)%13
            color = colors[2] if phase==0 else colors[1] if phase in (1,2,3) else tuple(c*config["background"]/100 for c in colors[0])
        else:
            left = min(1,int(t*2))
            f = min(1,t*2-left)
            color = tuple(colors[left][i]*(1-f)+colors[left+1][i]*f for i in range(3))
        result[slot] = hex_color(color)
    if config["effect"] == "custom":
        for slot,color in config["overrides"].items():
            result[int(slot)] = color
    return result

def payload(config):
    return b"".join(bytes((0,*rgb(c))) for c in render_colors(config))

def packet(kind, mode=0, speed=0, brightness=0, color=0, direction=0):
    data = bytes((kind,0,mode,speed,brightness,color,direction))
    return b"\x00" + data + bytes((255-(sum(data)&255),))

def checked_name(value):
    if not isinstance(value,str) or not 1 <= len(value.strip()) <= 48 or any(ord(c)<32 for c in value):
        raise ValueError("Give your profile a name of 1–48 characters.")
    return value.strip()
