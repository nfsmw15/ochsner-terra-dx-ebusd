#!/usr/bin/env python3
"""Schematic of the heating system (SVG) plus the positions of the live values on top of it.

The SVG and the picture-elements positions come from the same coordinates, so values always sit
inside their box. Hydraulics: TERRA DX 5 HCUA, variant M2-1 (internal 3-way diverter WW/HZ in the
flow), external 3-way diverter in the common return (tank bottom or HZ-VL tee), UNI800 combi tank,
heating circuit via Oventrop Regumat M3-180 (3-way mixer 01-021, pump 01-020, mixer sensor TMK).

Besides the base image, transparent overlay layers with the same viewBox are written (flow_*.svg,
valves_*.svg); the dashboard shows them conditionally, so the water flow is animated per valve position.

Usage: schema.py OUTDIR [PREVIEW.svg STATES.json]
"""
import json, os, sys

W, H = 1000, 620
GREY, RED, BLUE, ORANGE, BROWN = "#7f8790", "#e5484d", "#3e9bdc", "#f5a524", "#8d6e4a"
OPEN, CLOSED = "#30a46c", "#e5484d"

# value boxes: key -> (x, y, w, h, title, x offset of the right column)
BOXES = {
    "aussen": (15, 40, 140, 62, "Außen", 0),
    "wp": (170, 40, 330, 106, "Wärmepumpe", 165),
    "ww": (560, 40, 340, 84, "Warmwasser", 170),
    "wpkreis": (185, 478, 370, 118, "Wärmepumpen-Kreis", 190),
    "hk": (580, 478, 405, 118, "Heizkreis Fußbodenheizung", 190),
}

# live values: (box, row, column, entity key, prefix, style); column 0 = left, 1 = right
VALUES = [
    ("aussen", 0, 0, "at", "", "big"),
    ("wp", 0, 0, "wp_status", "", "text"),
    ("wp", 0, 1, "ventile", "Ventile: ", "text"),
    ("wp", 1, 0, "leistung", "Wärme ", "big"),
    ("wp", 1, 1, "verdichter", "Verdichter ", "small"),
    ("wp", 2, 0, "p_el", "Strom ", "small"),
    ("wp", 2, 1, "cop", "COP ", "small"),
    ("ww", 0, 0, "tb", "Ist ", "big"),
    ("ww", 0, 1, "ww_soll", "Soll ", "soll"),
    ("ww", 1, 0, "ww_status", "", "text"),
    ("wpkreis", 0, 0, "twv", "Vorlauf ", "red"),
    ("wpkreis", 0, 1, "spreizung", "Spreizung ", "small"),
    ("wpkreis", 1, 0, "twr", "Rücklauf ", "blue"),
    ("wpkreis", 1, 1, "flow", "Durchfluss ", "small"),
    ("wpkreis", 2, 0, "wp_pumpe", "Pumpe ", "small"),
    ("hk", 0, 0, "hk_vl", "Ist ", "orange"),
    ("hk", 0, 1, "hk_soll", "Soll ", "soll"),
    ("hk", 1, 0, "mischer", "Mischer ", "small"),
    ("hk", 2, 0, "hk_status", "", "text"),
]

# values drawn directly on a component: (x, y, entity key, prefix, style)
FREE = [
    (580, 252, "tpo", "oben ", "tank"),
    (580, 322, "tpm", "Mitte ", "tank"),
    (580, 343, "anlage_soll", "Soll ", "soll"),
]

ICONS = [  # (x, y, entity key, icon)
    (780, 300, "hk_pumpe", "mdi:pump"),
    (975, 20, "sammel", "mdi:alert-circle"),
]

HEADLINE = (500, 18, "zustand")

# sensor dots: (dot, start of the leader line at the box edge or None, name)
SENSORS = [
    ((650, 205), (600, 124), "TB"),
    ((650, 252), None, "TPO"),
    ((650, 330), None, "TPM"),
    ((295, 400), (295, 478), "TWV"),
    ((415, 425), (415, 478), "TWR"),
    ((805, 300), (805, 478), "TMK"),
]

# pipe geometry shared by the base image and the flow layers
INT_VALVE, EXT_VALVE, MIXER = (325, 330), (465, 425), (722, 300)
WP_FLOW_WW = "M266 400 H325 V260 H510"                     # compressor -> internal valve -> WW-Vorlauf
WP_FLOW_HZ = "M266 400 H325 V330 H385 V380 H510"           # compressor -> internal valve -> HZ-Vorlauf
WP_RET_WW = "M510 380 H465 V425 H240 V426"                 # tank (HZ-VL port) -> tee -> external valve -> WP
WP_RET_HZ = "M510 425 H240 V426"                           # tank bottom -> external valve -> WP
HK_FLOW = "M650 300 H820 V230 H955 V262 H845 V294 H955 V326 H845 V358 H955 V400 H722 V300"
HK_RET = "M722 400 H650"


def row_y(box, row):
    return BOXES[box][1] + 42 + row * 24


def col_x(box, col):
    x, _, _, _, _, off = BOXES[box]
    return x + 12 if col == 0 else x + off


def placements():
    """All live values as (x, y, key, prefix, style, anchor) in SVG units."""
    out = [(col_x(b, c), row_y(b, r), k, p, s, "start") for b, r, c, k, p, s in VALUES]
    out += [(x, y, k, p, s, "middle") for x, y, k, p, s in FREE]
    out.append((HEADLINE[0], HEADLINE[1], HEADLINE[2], "", "head", "middle"))
    return out


def port(cx, cy, p, r=17, h=12):
    """Triangle of one valve port ('l', 'r', 't', 'b') pointing to the valve centre."""
    a, b = {"l": ((cx - r, cy - h), (cx - r, cy + h)), "r": ((cx + r, cy - h), (cx + r, cy + h)),
            "t": ((cx - h, cy - r), (cx + h, cy - r)), "b": ((cx - h, cy + r), (cx + h, cy + r))}[p]
    return '<polygon points="%d,%d %d,%d %d,%d"/>' % (*a, *b, cx, cy)


def valve(c, ports):
    return "".join(port(*c, p) for p in ports)


def pipe(d, color, width=6, extra=""):
    return '<path d="%s" stroke="%s" stroke-width="%d" fill="none" stroke-linejoin="round"%s/>' % (d, color, width, extra)


def arrow(x, y, direction, color):
    pts = {"r": (x - 12, y - 7, x, y, x - 12, y + 7), "l": (x + 12, y - 7, x, y, x + 12, y + 7)}[direction]
    return '<polygon points="%d,%d %d,%d %d,%d" fill="%s"/>' % (*pts, color)


def head():
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="Segoe UI, Roboto, sans-serif">' % (W, H)


def svg():
    s = [head(),
         "  <!-- generated by tools/schema.py – Ochsner TERRA DX 5 HCUA (M2-1), UNI800, Regumat M3 mixer circuit -->",
         """  <defs>
    <linearGradient id="tank" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e5484d" stop-opacity="0.55"/>
      <stop offset="0.55" stop-color="#f5a524" stop-opacity="0.35"/>
      <stop offset="1" stop-color="#3e9bdc" stop-opacity="0.35"/>
    </linearGradient>
    <linearGradient id="soil" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#8d6e4a" stop-opacity="0.2"/>
      <stop offset="1" stop-color="#8d6e4a" stop-opacity="0.5"/>
    </linearGradient>
  </defs>"""]
    # ground and closed collector loop (leaves the heat pump on its left side)
    s.append('<rect x="0" y="465" width="%d" height="%d" fill="url(#soil)"/>' % (W, H - 465))
    s.append('<line x1="0" y1="465" x2="%d" y2="465" stroke="%s" stroke-width="3"/>' % (W, BROWN))
    s.append(pipe("M185 420 H165 V505 H40 Q20 505 20 525 Q20 545 40 545 H130 Q150 545 150 565 Q150 585 130 585 H40 "
                  "Q20 585 20 600 V608 H177 V440 H185", "#c98a3c", 5, ' stroke-linecap="round"'))
    s.append('<text x="22" y="492" font-size="12" fill="%s">Erdkollektor</text>' % BROWN)

    # heat pump with compressor and internal diverter (M2-1)
    s.append('<rect x="185" y="150" width="180" height="300" rx="14" fill="%s" fill-opacity="0.12" stroke="%s" stroke-width="3"/>' % (GREY, GREY))
    s.append('<text x="275" y="176" font-size="17" fill="%s" text-anchor="middle" font-weight="600">TERRA DX 5</text>' % GREY)
    s.append('<text x="275" y="194" font-size="11" fill="%s" text-anchor="middle">Variante M2-1</text>' % GREY)
    s.append('<circle cx="240" cy="400" r="26" fill="none" stroke="%s" stroke-width="3"/>' % GREY)
    s.append('<path d="M224 400 L240 382 L256 400 L240 418 Z" fill="%s" fill-opacity="0.35"/>' % GREY)
    s.append(pipe("M266 400 H325 V347", RED))
    s.append(pipe("M325 313 V260 H498", RED))
    s.append(pipe("M342 330 H385 V380 H498", RED))
    s.append(arrow(510, 260, "r", RED) + arrow(510, 380, "r", RED))
    s.append(pipe("M465 380 V408", RED, 4))
    s.append(pipe("M482 425 H510", BLUE))
    s.append(pipe("M448 425 H240 V426", BLUE))
    s.append(arrow(367, 425, "l", BLUE))
    s.append('<g fill="%s" fill-opacity="0.35" stroke="%s" stroke-width="2.5" stroke-linejoin="round">%s%s</g>'
             % (GREY, GREY, valve(INT_VALVE, "tbr"), valve(EXT_VALVE, "tlr")))
    s.append('<text x="425" y="252" font-size="12" fill="%s" text-anchor="middle">WW-Vorlauf</text>' % GREY)
    s.append('<text x="435" y="372" font-size="12" fill="%s" text-anchor="middle">HZ-Vorlauf</text>' % GREY)
    s.append('<text x="296" y="322" font-size="10" fill="%s" text-anchor="middle">intern</text>' % GREY)
    s.append('<text x="465" y="458" font-size="10" fill="%s" text-anchor="middle">Umschaltventil extern</text>' % GREY)

    # UNI800 with stainless corrugated pipe for domestic hot water
    s.append('<rect x="510" y="160" width="140" height="300" rx="40" fill="url(#tank)" stroke="%s" stroke-width="3"/>' % GREY)
    s.append('<path d="M540 450 C 565 435, 595 435, 620 420 S 565 395, 540 380 S 595 355, 620 340 S 565 315, 540 300 '
             'S 595 275, 620 260 S 565 235, 540 220 S 595 200, 605 185 V160" fill="none" stroke="%s" stroke-width="2.5" stroke-opacity="0.5"/>' % GREY)
    s.append('<text x="550" y="150" font-size="17" fill="%s" text-anchor="middle" font-weight="600">UNI800</text>' % GREY)
    s.append(pipe("M605 160 V135 H905", RED, 4, ' stroke-opacity="0.85"'))
    s.append('<path d="M905 135 H925 V150 M912 156 H938 M916 166 l-4 9 M925 166 v11 M934 166 l4 9" stroke="%s" '
             'stroke-width="3" fill="none" stroke-linecap="round"/>' % BLUE)
    s.append(pipe("M540 460 V475", BLUE, 4, ' stroke-opacity="0.85"'))

    # heating circuit: tank -> Regumat mixer -> pump -> TMK -> floor heating -> return (tee to mixer)
    s.append(pipe("M650 300 H705", RED))
    s.append(pipe("M739 300 H820", ORANGE))
    s.append(pipe("M820 300 V230 H955 V262 H845 V294 H955 V326 H845 V358 H955 V400 H722 V317", ORANGE, 5,
                  ' stroke-linecap="round"'))
    s.append(pipe("M722 400 H662", BLUE))
    s.append(arrow(650, 400, "l", BLUE))
    s.append('<g fill="%s" fill-opacity="0.35" stroke="%s" stroke-width="2.5" stroke-linejoin="round">%s</g>'
             % (GREY, GREY, valve(MIXER, "lrb")))
    s.append('<circle cx="780" cy="300" r="15" fill="none" stroke="%s" stroke-width="2.5"/>' % GREY)
    s.append('<text x="722" y="272" font-size="11" fill="%s" text-anchor="middle">Mischer</text>' % GREY)
    s.append('<text x="900" y="220" font-size="13" fill="%s" text-anchor="middle">Fußbodenheizung</text>' % GREY)

    # value boxes, sensors and leader lines
    for x, y, w, h, title, _ in BOXES.values():
        s.append('<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="%s" fill-opacity="0.12" stroke="%s" stroke-width="1.5"/>'
                 % (x, y, w, h, GREY, GREY))
        s.append('<text x="%d" y="%d" font-size="13" fill="%s" font-weight="600">%s</text>' % (x + 12, y + 18, GREY, title))
    for (sx, sy), lead, name in SENSORS:
        if lead:
            s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.5" stroke-dasharray="4 3"/>'
                     % (*lead, sx, sy, GREY))
        s.append('<circle cx="%d" cy="%d" r="5" fill="#fff" stroke="%s" stroke-width="2"/>' % (sx, sy, GREY))
        s.append('<text x="%d" y="%d" font-size="10" fill="%s">%s</text>' % (sx + 8, sy - 7, GREY, name))
    s.append("</svg>")
    return "\n".join(s) + "\n"


FLOW_CSS = ("<style>.f{fill:none;stroke:#fff;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round;"
            "stroke-dasharray:5 15;opacity:.9;animation:m .9s linear infinite}"
            "@keyframes m{to{stroke-dashoffset:-20}}</style>")


def flow_layer(*paths):
    """Transparent layer with moving dashes along the given paths (path direction = flow direction)."""
    return head() + FLOW_CSS + "".join('<path class="f" d="%s"/>' % d for d in paths) + "</svg>\n"


def valve_layer(int_open, int_closed, ext_open, ext_closed):
    """Transparent layer that colours the open (green) and closed (red) ports of both diverters."""
    def g(color, body):
        return '<g fill="%s" fill-opacity="0.9" stroke="%s" stroke-width="2" stroke-linejoin="round">%s</g>' % (color, color, body)
    return (head() + g(OPEN, port(*INT_VALVE, int_open) + port(*EXT_VALVE, ext_open))
            + g(CLOSED, port(*INT_VALVE, int_closed) + port(*EXT_VALVE, ext_closed)) + "</svg>\n")


LAYERS = {
    "flow_ww.svg": lambda: flow_layer(WP_FLOW_WW, WP_RET_WW),
    "flow_hz.svg": lambda: flow_layer(WP_FLOW_HZ, WP_RET_HZ),
    "flow_hk.svg": lambda: flow_layer(HK_FLOW, HK_RET),
    # internal valve: t = WW-Vorlauf, r = HZ-Vorlauf; external valve: t = HZ-VL tee, r = tank bottom
    "valves_ww.svg": lambda: valve_layer("t", "r", "t", "r"),
    "valves_hz.svg": lambda: valve_layer("r", "t", "r", "t"),
}


def write_all(outdir):
    open(os.path.join(outdir, "anlage.svg"), "w").write(svg())
    for name, make in LAYERS.items():
        open(os.path.join(outdir, name), "w").write(make())


PREVIEW_STYLE = {"big": (17, "600", None), "red": (17, "600", RED), "blue": (17, "600", BLUE), "orange": (17, "600", ORANGE),
                 "tank": (15, "600", None), "soll": (15, "400", None), "small": (15, "400", None), "text": (15, "400", None),
                 "head": (18, "600", None)}


PREVIEW_UNIT = {"at": " °C", "tb": " °C", "ww_soll": " °C", "twv": " °C", "twr": " °C", "hk_vl": " °C", "hk_soll": " °C",
                "tpo": " °C", "tpm": " °C", "anlage_soll": " °C", "spreizung": " K", "flow": " L/min", "leistung": " kW",
                "verdichter": " %", "mischer": " %", "wp_pumpe": " %", "p_el": " W"}


def preview(states, entities, layers=()):
    """SVG with sample values (about the size HA renders them) and the given layers, to check the layout."""
    body = svg().rsplit("</svg>", 1)[0]
    for name in layers:
        body += LAYERS[name]().split(">", 1)[1].rsplit("</svg>", 1)[0]
    for x, y, key, prefix, style, anchor in placements():
        size, weight, color = PREVIEW_STYLE[style]
        val = states.get(entities.get(key, ""), "–")
        val += PREVIEW_UNIT.get(key, "") if val not in ("–", "unknown", "unavailable") else ""
        body += '<text x="%d" y="%d" font-size="%d" font-weight="%s" fill="%s" text-anchor="%s" dominant-baseline="middle">%s%s</text>\n' % (
            x, y, size, weight, color or "#333", anchor, prefix, val)
    return body + "</svg>\n"


if __name__ == "__main__":
    write_all(sys.argv[1])
    if len(sys.argv) > 3:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from dashboard import E
        states = json.load(open(sys.argv[3]))
        open(sys.argv[2], "w").write(preview(states, E, sys.argv[4].split(",") if len(sys.argv) > 4 else ()))
