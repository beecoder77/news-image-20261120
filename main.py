#!/usr/bin/env python3
"""news-image-20261120 — one-day world news front page, drawn in code.

Draws a 1024x1024 newspaper front page for Friday 20 November 2026 and writes
it to $MAKEFUN_OUTPUT_DIR/entry.png. Pure Python 3.13 standard library:
own PNG encoder (zlib/struct), own 5x7 bitmap font, own vector drawing.
No network, no randomness, no timestamps: two runs write identical bytes.

Stories: 42, verified against named sources in research-20nov.md.
Lead: Cyclone Akvan landfall (Odisha, noon IST). Also featured: Trump defers
the Iran decision to 2027; ICJ finds Myanmar guilty of genocide.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# --- palette ---------------------------------------------------------------
PAPER = (253, 246, 227)   # cream newsprint
INK = (26, 26, 26)        # near-black
RED = (178, 34, 34)       # headline red
BLUE = (30, 64, 175)      # deep blue
GREY = (110, 105, 95)     # muted grey
LIGHT = (238, 228, 205)   # pale panel
SEA = (163, 196, 216)     # sea blue for the cyclone panel
LAND = (214, 196, 158)    # sand for the coastline panel
WHITE = (255, 255, 255)
DARK = (20, 24, 40)       # wire-strip band


# --- canvas ----------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.buf = bytearray(bytes(bg) * (w * h))

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._off(x, y)
            self.buf[o:o + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            o = self._off(x0, yy)
            self.buf[o:o + len(row)] = row

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c):
        """Bresenham line."""
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=False):
        if fill:
            for yy in range(-r, r + 1):
                half = int(math.sqrt(max(0, r * r - yy * yy)))
                self.rect(cx - half, cy + yy, 2 * half + 1, 1, c)
            return
        steps = max(24, int(2 * math.pi * r))
        for i in range(steps + 1):
            a = 2 * math.pi * i / steps
            self.px(cx + int(r * math.cos(a)), cy + int(r * math.sin(a)), c)

    def arc(self, cx, cy, r, a0, a1, c):
        steps = max(8, int(abs(a1 - a0) * r))
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            self.px(cx + int(r * math.cos(a)), cy + int(r * math.sin(a)), c)

    def ellipse(self, cx, cy, rx, ry, c, fill=True):
        if not fill:
            steps = max(24, int(2 * math.pi * max(rx, ry)))
            for i in range(steps + 1):
                a = 2 * math.pi * i / steps
                self.px(cx + int(rx * math.cos(a)), cy + int(ry * math.sin(a)), c)
            return
        for yy in range(-ry, ry + 1):
            t = 1.0 - (yy * yy) / float(ry * ry)
            half = int(rx * math.sqrt(max(0.0, t)))
            self.rect(cx - half, cy + yy, 2 * half + 1, 1, c)


# --- PNG encoder (stdlib only) ---------------------------------------------
def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def write_png(path, cv):
    raw = bytearray()
    rowlen = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.buf[y * rowlen:(y + 1) * rowlen]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# --- 5x7 bitmap font --------------------------------------------------------
# One 35-char string per glyph: 7 rows of 5 bits, top row first.
# Written by hand in this session (classic 5x7 patterns).
GLYPHS = {
' ': '00000000000000000000000000000000000',
'!': '00100001000010000100001000000000100',
'"': '01010010100101000000000000000000000',
'#': '01010010101111101010111110101001010',
'$': '00100011111010001110001011111000100',
'%': '11001110100001000100010000101110011',
'&': '01100100101010001000101011001001101',
"'": '00100001000100000000000000000000000',
'(': '00010001000100001000010000010000010',
')': '01000001000001000010000100010001000',
'*': '00000001001010101110101010010000000',
'+': '00000001000010011111001000010000000',
',': '00000000000000000000001000010001000',
'-': '00000000000000001110000000000000000',
'.': '00000000000000000000000000110001100',
'/': '00001000100001000100010000100010000',
'0': '01110100011001110101110011000101110',
'1': '00100011000010000100001000010001110',
'2': '01110100010000100110010001000011111',
'3': '11111000100010000010000011000101110',
'4': '00010001100101010010111110001000010',
'5': '11111100001111000001000011000101110',
'6': '00110010001000011110100011000101110',
'7': '11111000010001000100010000100001000',
'8': '01110100011000101110100011000101110',
'9': '01110100011000101111000010001001100',
':': '00000011000110000000011000110000000',
';': '00000011000110000000011000110001000',
'<': '00010001000100010000010000010000010',
'=': '00000000001111100000111110000000000',
'>': '01000001000001000001000100010001000',
'?': '01110100010000100010001000000000100',
'@': '01110100011011110101101101000001110',
'A': '01110100011000111111100011000110001',
'B': '11110100011000111110100011000111110',
'C': '01110100011000010000100001000101110',
'D': '11110100011000110001100011000111110',
'E': '11111100001000011110100001000011111',
'F': '11111100001000011110100001000010000',
'G': '01110100011000010111100011000101111',
'H': '10001100011000111111100011000110001',
'I': '01110001000010000100001000010001110',
'J': '00111000100001000010000101001001100',
'K': '10001100101010011000101001001010001',
'L': '10000100001000010000100001000011111',
'M': '10001110111010110101100011000110001',
'N': '10001110011010110011100011000110001',
'O': '01110100011000110001100011000101110',
'P': '11110100011000111110100001000010000',
'Q': '01110100011000110001101011001001101',
'R': '11110100011000111110101001001010001',
'S': '01111100001000001110000010000111110',
'T': '11111001000010000100001000010000100',
'U': '10001100011000110001100011000101110',
'V': '10001100011000110001100010101000100',
'W': '10001100011000110101101011101110001',
'X': '10001100010101000100010101000110001',
'Y': '10001100010101000100001000010000100',
'Z': '11111000010001000100010001000011111',
'[': '01110010000100001000010000100001110',
'\\': '10000010000100000100000100001000001',
']': '01110000100001000010000100001001110',
'^': '00100010101000100000000000000000000',
'_': '00000000000000000000000000000011111',
'`': '00100001000001000000000000000000000',
'a': '00000000000111000001011111000101111',
'b': '10000100001111010001100011000111110',
'c': '00000000000111010000100001000101110',
'd': '00001000010111110001100011000101111',
'e': '00000000000111010001111111000001110',
'f': '00110010010100011110010000100001000',
'g': '00000011111000110001011110000101110',
'h': '10000100001111010001100011000110001',
'i': '00100000000110000100001000010001110',
'j': '00010000000011000010000101001001100',
'k': '10000100001001010100110001010010010',
'l': '01100001000010000100001000010001110',
'm': '00000000001101010101101011010110101',
'n': '00000000001111010001100011000110001',
'o': '00000000000111010001100011000101110',
'p': '00000000001111010001111101000010000',
'q': '00000000000111110001011110000100001',
'r': '00000000001011011001100001000010000',
's': '00000000000111110000011100000111110',
't': '01000010001110001000010000100100110',
'u': '00000000001000110001100011001101101',
'v': '00000000001000110001100010101000100',
'w': '00000000001000110101101011010101010',
'x': '00000000001000101010001000101010001',
'y': '00000000001000110001011110000101110',
'z': '00000000001111100010001000100011111',
'{': '00010001000010001100001000010000010',
'|': '00100001000010000100001000010000100',
'}': '01000001000010000110001000010001000',
'~': '00000000000100110110000000000000000',
}

# Characters outside the font are normalised to plain ASCII first.
_NORMALISE = {"\u2019": "'", "\u2018": "'", "\u2013": "-",
              "\u2014": "-", "\u2022": "-", "\u00d7": "x", "\u201c": '"',
              "\u201d": '"'}


def _glyph(ch):
    ch = _NORMALISE.get(ch, ch)
    return GLYPHS.get(ch, GLYPHS["?"])


def text_w(s, scale, spacing=1):
    return len(s) * (5 * scale + spacing) - spacing if s else 0


def draw_text(cv, x, y, s, scale, color, bold=False, spacing=1):
    """Draw text with the 5x7 font; returns the x after the last character."""
    cx = x
    adv = 5 * scale + spacing
    for ch in s:
        g = _glyph(ch)
        for r in range(7):
            row = g[r * 5:(r + 1) * 5]
            for c in range(5):
                if row[c] == "1":
                    cv.rect(cx + c * scale, y + r * scale, scale, scale, color)
                    if bold:
                        cv.rect(cx + c * scale + 1, y + r * scale,
                                scale, scale, color)
        cx += adv
    return cx


def draw_centred(cv, cx, y, s, scale, color, bold=False):
    draw_text(cv, cx - text_w(s, scale) // 2, y, s, scale, color, bold)


def wrap(s, max_chars):
    """Greedy word wrap; returns a list of lines, each <= max_chars."""
    lines, cur = [], ""
    for word in s.split(" "):
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= max_chars:
            cur += " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def badge(cv, x, y, num, size=16):
    """Small red square with a white number, for the map-marker stories."""
    cv.rect(x, y, size, size, RED)
    s = str(num)
    draw_centred(cv, x + size // 2, y + (size - 7) // 2, s, 1, WHITE, True)


# --- story data --------------------------------------------------------------
# (headline, detail, map-badge or None). Headlines/details are uppercase
# and capped at 29 chars (grid column fits 29 chars at scale 2).
# Sources per story: research-20nov.md.
COLUMNS = [
    [("NORTH AMERICA", [
        ("TRUMP TO BRIEF WHITE HOUSE", "AFTER SHENZHEN SUMMIT", None),
        ("ANTHROPIC'S $2TN DEBUT", "SHARES +17% TO $97.17", 7),
        ("GTA VI SALES TOP $1.8BN", "19.1M COPIES (ESTIMATE)", None),
        ("VOYAGER 1 A LIGHT-DAY AWAY", "FIRST OBJECT SO FAR - NASA", 8),
        ("CRUDE FUTURES FALL 3%", "STOCKS END TWO-DAY RALLY", None),
    ]),
     ("LATIN AMERICA", [
        ("LULA IN NO RUSH ON CABINET", "NEW TERM STARTS IN JANUARY", None),
        ("BRAZIL PASSES FISCAL BILL", "SENATE APPROVES ADJUSTMENT", None),
        ("VENEZUELA'S LEADER TOURS GULF", "IN TURKEY, QATAR AND UAE", None),
    ]),
     ("SCIENCE & TECH", [
        ("HAYABUSA2 ABANDONS LANDING", "ENGINE TROUBLE, NEW PLAN", None),
        ("NVIDIA CHIEF OUSTED", "ESPIONAGE CASE, NYT REPORTS", None),
        ("GTA VI ALBUM OUT TODAY", "SOUNDTRACK RELEASED 20 NOV", None),
        ("WORLD CHILDREN'S DAY TODAY", "20 NOVEMBER OBSERVANCE", None),
        ("IFFI ADDS ANIMATION SECTION", "FIVE FILMS IN NEW GOA STRAND", None),
    ])],
    [("EUROPE", [
        ("EUROPE READY FOR RUSSIA TALKS", "BERLIN: KYIV MUST AGREE", None),
        ("KYIV DRONES HIT EMBASSIES", "1 KILLED; CATHEDRAL DAMAGED", 6),
        ("PUTIN INVITES EUROPE TO TALK", "COME TO MOSCOW, HE SAYS", None),
        ("UKRAINE HITS CRIMEAN BRIDGE", "RUTA MISSILES, REPORTS SAY", None),
        ("COP31 TALKS DEADLOCKED", "NATIONS LAUNCH REALITY CHECK", None),
        ("BIG THREE VOW NUCLEAR TALKS", "TRUMP, XI, PUTIN MEET", 5),
    ]),
     ("MIDDLE EAST", [
        ("PIF TOWER DAMAGED IN RIYADH", "DEBRIS HIT; NO INJURIES", 4),
        ("COALITION DOWNS FOUR MISSILES", "SAADA LAUNCH SITE DESTROYED", None),
        ("GULF CONDEMNS RIYADH ATTACK", "QATAR, KUWAIT, GCC SPEAK OUT", None),
        ("ISRAEL MAY ACT ALONE ON IRAN", "ENVOY WARNS ON TEHRAN REGIME", None),
        ("COALITION STRIKES SANAA", "HOUTHI MEDIA REPORT RAIDS", None),
    ]),
     ("SPORT", [
        ("NICHOLLS TON LIFTS NZ", "243/5 AT STUMPS, DAY 1", None),
        ("INDIA WIN BADMINTON TIE", "BEAT MALAYSIA IN HONG KONG", None),
    ])],
    [("AFRICA", [
        ("DR CONGO: FIGHTERS MUST LEAVE", "UN HAS A WEEK TO FLY OUT 750", None),
        ("SUDAN DRONE WAR GRINDS ON", "POWER GRID HIT; RETURNS BEGIN", None),
        ("EBOLA CASES DOUBLE IN CONGO", "OUTBREAK SPREADS IN EAST", None),
        ("AI JOINS POLIO FIGHT", "WHO BOOSTS SURVEILLANCE", None),
        ("UAE JAILS 8 OVER SUDAN ARMS", "LIFE TERMS FOR SUPPLYING ARMY", None),
    ]),
     ("ASIA-PACIFIC", [
        ("SEOUL FREES HAN DUCK-SOO", "CONVICTION OVERTURNED", None),
        ("FIJI DROUGHT DISASTER", "EL NINO DRIES UP WATER SUPPLY", None),
        ("FIRE AT YUNUS FAMILY HOME", "FOUL PLAY SUSPECTED", None),
        ("MODI MEETS WILLIAM AND KATE", "ROYALS VISIT NEW DELHI", None),
        ("INDIA INKS MISSILE DEAL", "RS1,976-CRORE NAVY UPGRADE", None),
        ("SENSEX, NIFTY RALLY IN MUMBAI", "SENSEX +1.21%; NIFTY +1.14%", None),
        ("NORTH KOREA EXPANDS YONGBYON", "IAEA: 'SERIOUS CONCERN'", None),
        ("APEC TALKS TRADE IN SHENZHEN", "LEADERS EYE OPEN TRADE, TECH", None),
    ])],
]

# Map markers: (number, lon, lat, nudge_x, nudge_y) -> placed by lon/lat.
MARKERS = [
    (1, 85.2, 19.4, 0, 0),      # Akvan landfall, Gopalpur
    (2, 51.4, 35.7, 2, -4),     # Trump-Iran, Tehran
    (3, 4.3, 52.1, 0, 0),       # ICJ, The Hague
    (4, 46.7, 24.7, -2, 4),     # PIF Tower, Riyadh
    (5, 114.1, 22.5, 0, 0),     # Shenzhen summit
    (6, 30.5, 50.5, 0, 0),      # Kyiv embassies
    (7, -74.0, 40.7, 0, 0),     # Anthropic, New York
    (8, -118.1, 34.1, 0, 0),    # Voyager 1, Pasadena
]

LEGEND = [
    ("1 AKVAN, ODISHA", "5 SHENZHEN"),
    ("2 IRAN DECISION", "6 KYIV"),
    ("3 ICJ, THE HAGUE", "7 ANTHROPIC"),
    ("4 PIF TOWER", "8 VOYAGER 1"),
]


# --- layout ------------------------------------------------------------------
def draw_masthead(cv):
    draw_text(cv, 16, 8, "THE WORLD IN ONE DAY", 4, INK, bold=True)
    s = "42 STORIES - 7 REGIONS"
    draw_text(cv, 1008 - text_w(s, 2), 14, s, 2, RED, bold=True)
    draw_text(cv, 16, 42, "FRIDAY 20 NOVEMBER 2026", 4, RED, bold=True)
    s = "WORLD CHILDREN'S DAY"
    draw_text(cv, 1008 - text_w(s, 2), 48, s, 2, INK, bold=True)
    draw_text(cv, 16, 72,
              "THE DAY'S NEWS, AS REPORTED OVERNIGHT - VERIFIED AGAINST NAMED SOURCES",
              2, GREY)
    cv.hline(16, 88, 992, INK, 2)


def draw_cyclone_panel(cv, x, y, w, h):
    cv.rect(x, y, w, h, SEA)
    # Land: India's east coast on the right, wavy edge.
    for yy in range(y, y + h):
        edge = x + w - 130 + int(18 * math.sin((yy - y) / 28.0))
        cv.rect(edge, yy, x + w - edge, 1, LAND)
    # Spiral: concentric arcs, rotating with radius.
    cx, cy = x + 130, y + 105
    for i, r in enumerate((16, 28, 42, 58, 76)):
        a0 = i * 0.9
        cv.arc(cx, cy, r, a0, a0 + 4.6, WHITE if i % 2 == 0 else INK)
    cv.circle(cx, cy, 10, INK, fill=True)
    cv.circle(cx, cy, 5, WHITE, fill=True)
    # Rain bands sweeping in from the sea.
    for k in range(5):
        bx = x + 18 + k * 26
        by = y + 30 + k * 30
        cv.line(bx, by, bx + 34, by + 12, WHITE)
        cv.line(bx, by + 4, bx + 34, by + 16, WHITE)
    # Landfall marker on the coast.
    mx, my = x + w - 128, y + 108
    cv.circle(mx, my, 7, RED, fill=True)
    cv.circle(mx, my, 7, INK)
    draw_text(cv, x + w - 118, y + 128, "GOPALPUR", 2, INK, bold=True)
    draw_text(cv, x + w - 196, y + 10, "WINDS 90-100 KM/H", 2, INK, bold=True)
    draw_text(cv, x + 16, y + h - 24, "BAY OF BENGAL", 2, INK, bold=True)
    cv.rect(x, y, w, 2, INK)
    cv.rect(x, y + h - 2, w, 2, INK)
    cv.rect(x, y, 2, h, INK)
    cv.rect(x + w - 2, y, 2, h, INK)


def draw_lead(cv):
    badge(cv, 16, 98, 1)
    draw_text(cv, 40, 100, "ASIA-PACIFIC - CYCLONE AKVAN", 2, RED, bold=True)
    draw_text(cv, 16, 122, "AKVAN MAKES LANDFALL", 5, INK, bold=True)
    draw_text(cv, 16, 172,
              "SEVERE CYCLONE CROSSES ODISHA COAST AT NOON IST;", 2, INK)
    draw_text(cv, 16, 190,
              "WINDS 90-100 KM/H; 300,000 EVACUATED, 423 RESCUE", 2, INK)
    draw_text(cv, 16, 208,
              "TEAMS OUT; SCHOOLS SHUT, 69 TRAINS CANCELLED", 2, INK)
    draw_text(cv, 16, 242, "LANDFALL 06:30 UTC - NEAR GOPALPUR", 2, RED, bold=True)
    draw_cyclone_panel(cv, 616, 94, 392, 190)


def draw_second_row(cv):
    for (bx, num, head, sum1, sum2) in (
            (16, 2, "TRUMP DEFERS IRAN DECISION TO 2027",
             "TELLS AXIOS: NO NEW STRIKES", "BEFORE 2027; ISRAEL MAY ACT ALONE"),
            (520, 3, "ICJ: MYANMAR GUILTY OF GENOCIDE",
             "FIRST STATE FOUND GUILTY OF GENOCIDE;", "9-6 RULING; REPARATIONS ORDERED")):
        cv.rect(bx, 292, 488, 90, LIGHT)
        badge(cv, bx + 12, 304, num)
        lines = wrap(head, 25)
        yy = 300
        for ln in lines:
            draw_text(cv, bx + 36, yy, ln, 3, INK, bold=True)
            yy += 24
        draw_text(cv, bx + 36, yy + 4, sum1, 2, INK)
        draw_text(cv, bx + 36, yy + 21, sum2, 2, INK)


def draw_wire(cv):
    cv.rect(0, 390, 1024, 44, DARK)
    draw_text(cv, 16, 398,
              "TOP OF THE WIRE | AKVAN LANDFALL 06:30 UTC | TRUMP: NO IRAN CALL TILL 2027",
              2, WHITE, bold=True)
    draw_text(cv, 16, 416,
              "ANTHROPIC +17% ON DEBUT | DR CONGO DEADLINE 00:01 UTC | VOYAGER 1 A LIGHT-DAY AWAY",
              2, WHITE, bold=True)


def draw_grid(cv):
    xs = (16, 348, 684)
    for col, x in zip(COLUMNS, xs):
        y = 442
        for header, briefs in col:
            draw_text(cv, x, y, header, 2, RED, bold=True)
            cv.hline(x, y + 16, 324, INK, 1)
            y += 22
            for head, detail, num in briefs:
                tx = x
                if num is not None:
                    badge(cv, x, y, num)
                    tx = x + 22
                assert text_w(head, 2) <= (324 if num is None else 302), head
                assert text_w(detail, 2) <= (324 if num is None else 302), detail
                draw_text(cv, tx, y, head, 2, INK, bold=True)
                draw_text(cv, tx, y + 15, detail, 2, GREY)
                y += 33
        # 13 briefs + 3 headers = 495px; column ends at y 937.


def draw_map_strip(cv):
    cv.hline(16, 940, 992, INK, 2)
    draw_text(cv, 16, 950, "WHERE IT HAPPENED", 2, RED, bold=True)
    # Stylised continents: filled sand ellipses on a pale sea band.
    cv.rect(16, 968, 624, 52, (232, 240, 244))
    for (ex, ey, rx, ry) in ((120, 988, 75, 15), (185, 1008, 26, 11),
                             (345, 973, 22, 7), (355, 995, 30, 17),
                             (470, 984, 95, 17), (545, 1012, 28, 7)):
        cv.ellipse(ex, ey, rx, ry, LAND, fill=True)
    for num, lon, lat, nx, ny in MARKERS:
        mx = int(16 + (lon + 170) / 360.0 * 624) + nx
        my = int(968 + (75 - lat) / 130.0 * 52) + ny
        cv.circle(mx, my, 7, RED, fill=True)
        cv.circle(mx, my, 7, INK)
        draw_centred(cv, mx, my - 3, str(num), 1, WHITE, True)
    for row, (left, right) in enumerate(LEGEND):
        draw_text(cv, 656, 964 + row * 15, left, 2, INK, bold=True)
        draw_text(cv, 850, 964 + row * 15, right, 2, INK, bold=True)


def build():
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)
    draw_lead(cv)
    draw_second_row(cv)
    draw_wire(cv)
    draw_grid(cv)
    draw_map_strip(cv)
    return cv


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out, exist_ok=True)
    cv = build()
    path = os.path.join(out, "entry.png")
    size = write_png(path, cv)
    print("wrote %s (%d bytes, %dx%d)" % (path, size, W, H))


if __name__ == "__main__":
    main()
