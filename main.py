#!/usr/bin/env python3
"""news-image-20261120 v2: dense newspaper front page, Friday 20 Nov 2026.

Draws a 1024x1024 front page entirely in code: own 5x7 bitmap font, own
vector drawing (cyclone spiral, coastline, world map, bar chart), own PNG
encoder (zlib/struct). Stdlib only, no network, no time, no randomness that
isn't a fixed-seed PRNG -- two runs write a byte-identical PNG.

    MAKEFUN_OUTPUT_DIR=out python3 main.py   # writes out/entry.png

All 45 stories verified against the research file (research-20nov.md):
figures come from named sources only; estimates are labelled as estimates;
the ICJ Myanmar ruling is a 19 Nov event and is presented as such.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (247, 242, 230)
INK = (18, 18, 18)
RED = (176, 32, 32)
BLUE = (31, 78, 121)
TEAL = (14, 94, 90)
GREY = (110, 108, 100)
LGREY = (214, 208, 194)
CREAM = (255, 243, 214)
SKY = (198, 222, 236)
SEA = (168, 200, 220)
LAND = (232, 222, 196)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GOLD = (184, 134, 11)

# ---------------------------------------------------------------- canvas

_px = bytearray(W * H * 3)


def set_px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        _px[i] = c[0]
        _px[i + 1] = c[1]
        _px[i + 2] = c[2]


def fill_rect(x, y, w, h, c):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            _px[i] = c[0]
            _px[i + 1] = c[1]
            _px[i + 2] = c[2]


def hline(x0, x1, y, c, t=1):
    for yy in range(y, y + t):
        for xx in range(max(0, x0), min(W, x1)):
            set_px(xx, yy, c)


def vline(x, y0, y1, c, t=1):
    for xx in range(x, x + t):
        for yy in range(max(0, y0), min(H, y1)):
            set_px(xx, yy, c)


def line(x0, y0, x1, y1, c, t=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        for a in range(t):
            for b in range(t):
                set_px(x + a, y + b, c)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def rect(x, y, w, h, c, t=1):
    hline(x, x + w, y, c, t)
    hline(x, x + w, y + h - t, c, t)
    vline(x, y, y + h, c, t)
    vline(x + w - t, y, y + h, c, t)


def circle(cx, cy, r, c, fill=False):
    if fill:
        for yy in range(cy - r, cy + r + 1):
            dx = int(math.sqrt(max(0, r * r - (yy - cy) ** 2)))
            hline(cx - dx, cx + dx + 1, yy, c)
    else:
        x, y, d = r, 0, 1 - r
        while x >= y:
            for sx, sy in ((x, y), (y, x), (-x, y), (-y, x),
                           (x, -y), (y, -x), (-x, -y), (-y, -x)):
                set_px(cx + sx, cy + sy, c)
            y += 1
            if d <= 0:
                d += 2 * y + 1
            else:
                x -= 1
                d += 2 * (y - x) + 1


def ellipse(cx, cy, rx, ry, c, fill=False):
    if fill:
        for yy in range(cy - ry, cy + ry + 1):
            t = (yy - cy) / float(ry)
            dx = int(rx * math.sqrt(max(0.0, 1.0 - t * t)))
            hline(cx - dx, cx + dx + 1, yy, c)
    else:
        for a in range(0, 361, 2):
            rad = math.radians(a)
            set_px(int(cx + rx * math.cos(rad)), int(cy + ry * math.sin(rad)), c)


def poly_fill(points, c):
    """Scanline fill of a polygon (list of (x, y))."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    for y in range(max(0, min(ys)), min(H, max(ys) + 1)):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / float(y1 - y0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            hline(int(xs[k]), int(xs[k + 1]) + 1, y, c)


def poly_line(points, c, t=1, close=False):
    pts = points + [points[0]] if close else points
    for i in range(len(pts) - 1):
        line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c, t)


def arc(cx, cy, r, a0, a1, c, t=1):
    a = a0
    while a <= a1:
        rad = math.radians(a)
        for dx in range(t):
            for dy in range(t):
                set_px(int(cx + r * math.cos(rad)) + dx,
                       int(cy + r * math.sin(rad)) + dy, c)
        a += 1.5


def hatch(x, y, w, h, c, gap=6):
    """Diagonal hatch inside a rectangle (clipped)."""
    for d in range(-h, w + h, gap):
        x0 = x + max(0, d)
        y0 = y + max(0, -d)
        x1 = x + min(w, d + h)
        y1 = y + min(h, w - d)
        if x1 > x0:
            line(x0, y0, x1, y1, c)


def dots(x, y, w, h, c, gap=5, off=0):
    for yy in range(y + off, y + h, gap):
        for xx in range(x + off, x + w, gap):
            if ((xx + yy) // gap) % 2 == 0:
                set_px(xx, yy, c)


# Fixed-seed PRNG (deterministic paper speckle).
_seed = 123456789


def _rnd():
    global _seed
    _seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return _seed


def speckle(x, y, w, h, c, density=900):
    for _ in range(density):
        sx = x + _rnd() % max(1, w)
        sy = y + _rnd() % max(1, h)
        set_px(sx, sy, c)


# ---------------------------------------------------------------- font
# 5x7 bitmap font, one glyph = 7 rows of 5 bits ('1' = ink).

FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    'a': ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    'b': ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    'c': ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    'd': ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    'e': ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    'f': ("00110", "01000", "01000", "11110", "01000", "01000", "01000"),
    'g': ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    'h': ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    'i': ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    'j': ("00010", "00000", "01100", "00100", "00100", "10010", "01100"),
    'k': ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    'l': ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    'm': ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    'n': ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    'o': ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    'p': ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    'q': ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    'r': ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    's': ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    't': ("00100", "00100", "11110", "00100", "00100", "00100", "00110"),
    'u': ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    'v': ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    'w': ("00000", "00000", "10001", "10001", "10101", "10101", "01010"),
    'x': ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    'y': ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    'z': ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '*': ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '=': ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '#': ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    '@': ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    '_': ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '[': ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    ']': ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
}

_SANITIZE = {
    '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
    '\u2013': '-', '\u2014': '-', '\u20b9': 'Rs', '\u00e9': 'e',
    '\u00e1': 'a', '\u00ed': 'i', '\u00f3': 'o', '\u00fa': 'u',
    '\u00f1': 'n', '\u00fc': 'u', '\u00e8': 'e', '\u00e0': 'a',
    '\u00b0': 'o', '\u00d7': 'x', '\u2022': '.', '\u00a0': ' ',
}


def clean(text):
    out = []
    for ch in text:
        if ch in _SANITIZE:
            out.append(_SANITIZE[ch])
        elif ch in FONT:
            out.append(ch)
        else:
            out.append(' ')
    return ''.join(out)


def text_w(text, scale=1):
    return len(clean(text)) * 6 * scale - scale


def draw_text(x, y, text, scale=1, color=INK, align='l'):
    text = clean(text)
    w = text_w(text, scale)
    if align == 'c':
        x -= w // 2
    elif align == 'r':
        x -= w
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph:
            for r, row in enumerate(glyph):
                for cix, bit in enumerate(row):
                    if bit == '1':
                        fill_rect(cx + cix * scale, y + r * scale,
                                  scale, scale, color)
        cx += 6 * scale
    return w


def wrap_text(text, max_w, scale=1):
    """Greedy word wrap; returns list of lines fitting max_w px."""
    text = clean(text)
    words = text.split(' ')
    lines = []
    cur = ''
    for word in words:
        trial = word if not cur else cur + ' ' + word
        if text_w(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_block(x, y, text, max_w, scale=1, color=INK, leading=9,
               max_lines=None):
    lines = wrap_text(text, max_w, scale)
    if max_lines is not None:
        lines = lines[:max_lines]
    for i, ln in enumerate(lines):
        draw_text(x, y + i * leading, ln, scale, color)
    return y + len(lines) * leading

# ---------------------------------------------------------------- art

def draw_cyclone(x, y, w, h):
    """Lead art: cyclone spiral over the Bay of Bengal / Odisha coast."""
    fill_rect(x, y, w, h, SKY)
    # sea bands
    for i in range(0, h, 14):
        hline(x, x + w, y + i, SEA if (i // 14) % 2 == 0 else SKY)
    # coastline: landmass on the left, sea on the right
    coast = [(x + 8, y + h), (x + 26, y + h - 30), (x + 20, y + h - 70),
             (x + 44, y + h - 110), (x + 30, y + h - 150),
             (x + 52, y + 12), (x + 78, y + 2), (x + 78, y + h)]
    poly_fill(coast, (226, 214, 178))
    poly_line(coast, INK, 2)
    draw_text(x + 10, y + h - 22, "INDIA", 1, BLUE)
    draw_text(x + 95, y + 8, "BAY OF", 1, BLUE)
    draw_text(x + 95, y + 18, "BENGAL", 1, BLUE)
    # cyclone centre + spiral arms
    cx = x + w - 118
    cy = y + h // 2 - 6
    circle(cx, cy, 12, WHITE, fill=True)
    circle(cx, cy, 12, INK)
    circle(cx, cy, 5, RED, fill=True)
    for arm in range(5):
        a0 = arm * 72
        for r in range(14, 96, 2):
            ang = math.radians(a0 + r * 2.6)
            px = int(cx + r * math.cos(ang))
            py = int(cy + r * 0.82 * math.sin(ang))
            if x + 60 < px < x + w - 4 and y + 4 < py < y + h - 4:
                fill_rect(px, py, 4, 4, WHITE)
                if r % 6 == 0:
                    fill_rect(px, py, 2, 2, BLUE)
    # rain bands (outer arcs)
    for rr in (104, 116):
        arc(cx, cy, rr, 200, 340, WHITE, 2)
        arc(cx, cy, rr, 20, 160, WHITE, 2)
    # wind arrows around the eye
    for a in (30, 110, 190, 270, 340):
        rad = math.radians(a)
        px = int(cx + 52 * math.cos(rad))
        py = int(cy + 44 * math.sin(rad))
        tx = int(px + 14 * math.cos(rad + 1.2))
        ty = int(py + 14 * math.sin(rad + 1.2))
        line(px, py, tx, ty, INK, 2)
        line(tx, ty, tx - 6, ty + 2, INK, 1)
    # landfall marker + short onshore arrow + labels
    lx, ly = x + 58, y + h // 2 + 8
    line(lx + 4, ly, lx + 44, ly - 14, RED, 2)
    line(lx + 44, ly - 14, lx + 36, ly - 12, RED, 1)
    line(lx + 44, ly - 14, lx + 38, ly - 6, RED, 1)
    circle(lx, ly, 4, RED, fill=True)
    draw_text(cx + 18, cy + 2, "EYE", 1, RED)
    draw_text(x + 120, y + h - 12, "LANDFALL ~NOON IST - 06:30 UTC", 1, RED)
    draw_text(x + w - 108, y + h - 34, "90-100 KM/H", 1, INK)
    draw_text(x + w - 108, y + h - 24, "GUSTING 110", 1, INK)
    draw_text(x + w - 108, y + h - 14, "ODISHA COAST", 1, INK)
    rect(x, y, w, h, INK, 2)


# Simplified continent outlines (lon, lat) -> drawn on the map strip.
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 72), (-110, 68), (-95, 69), (-85, 66),
     (-80, 62), (-75, 58), (-65, 60), (-60, 52), (-55, 47), (-70, 44),
     (-75, 38), (-80, 32), (-84, 30), (-90, 29), (-97, 26), (-105, 22),
     (-110, 24), (-115, 30), (-120, 34), (-125, 40), (-125, 49),
     (-135, 58), (-150, 60), (-165, 60), (-168, 66)],
    # South America
    [(-80, 9), (-75, 11), (-65, 11), (-60, 8), (-52, 5), (-50, 0),
     (-45, -5), (-35, -8), (-40, -20), (-48, -28), (-58, -38),
     (-65, -45), (-70, -52), (-73, -40), (-72, -25), (-70, -18),
     (-77, -12), (-81, -5), (-80, 9)],
    # Europe
    [(-10, 36), (-9, 43), (-2, 48), (-4, 50), (0, 51), (5, 53), (8, 57),
     (10, 59), (18, 56), (21, 55), (24, 59), (28, 61), (30, 60),
     (32, 70), (40, 68), (44, 68), (45, 60), (40, 55), (35, 50),
     (30, 46), (28, 44), (23, 40), (19, 42), (12, 44), (8, 44),
     (3, 43), (0, 39), (-2, 37), (-10, 36)],
    # Africa
    [(-17, 15), (-16, 20), (-10, 30), (0, 35), (10, 37), (20, 32),
     (30, 31), (35, 28), (38, 22), (43, 12), (51, 11), (48, 2),
     (40, -5), (40, -15), (35, -25), (28, -33), (20, -35), (16, -28),
     (12, -18), (9, -2), (9, 4), (-8, 5), (-13, 8), (-17, 15)],
    # Asia
    [(-10, 36), (30, 36), (36, 36), (43, 39), (48, 38), (52, 38),
     (56, 40), (60, 45), (66, 44), (70, 42), (75, 40), (78, 36),
     (80, 30), (85, 22), (88, 21), (92, 21), (95, 16), (100, 13),
     (104, 8), (108, 11), (110, 20), (115, 23), (120, 28), (122, 32),
     (127, 35), (130, 38), (135, 43), (140, 45), (142, 50), (140, 55),
     (145, 60), (155, 60), (160, 65), (170, 66), (178, 65), (178, 62),
     (170, 60), (160, 55), (150, 45), (140, 40), (135, 35), (130, 33),
     (125, 40), (120, 45), (110, 50), (100, 55), (90, 60), (80, 65),
     (70, 68), (60, 68), (55, 70), (45, 68), (40, 68), (35, 66),
     (32, 70), (30, 60), (28, 61), (24, 59), (21, 55), (18, 56)],
    # Australia
    [(114, -22), (114, -30), (118, -35), (125, -33), (130, -32),
     (135, -35), (140, -38), (146, -39), (150, -37), (153, -27),
     (150, -22), (146, -19), (142, -15), (142, -11), (136, -12),
     (132, -11), (126, -14), (122, -17), (118, -20), (114, -22)],
]

# (number, label, lon, lat) for the numbered map markers.
MARKERS = [
    (1, "AKVAN LANDFALL - ODISHA, INDIA", 86, 19),
    (2, "ICJ RULING - THE HAGUE", 4, 52),
    (3, "HOUTHI MISSILE - RIYADH", 47, 25),
    (4, "DRONE RAID - KYIV", 31, 50),
    (5, "UKRAINE TALKS - BERLIN", 13, 52),
    (6, "TRUMP-XI-PUTIN - SHENZHEN", 114, 22),
    (7, "TRUMP / ANTHROPIC - WASHINGTON", -77, 39),
    (8, "UN FLY-OUT - GOMA, DR CONGO", 29, -1),
]


def draw_map(x, y, w, h):
    fill_rect(x, y, w, h, SEA)
    # graticule
    for gx in range(x + 40, x + w, 40):
        vline(gx, y, y + h, (190, 212, 228))
    for gy in range(y + 18, y + h, 18):
        hline(x, x + w, gy, (190, 212, 228))
    lon0, lon1 = -180, 180
    lat0, lat1 = 78, -58

    def proj(lon, lat):
        px = x + (lon - lon0) / float(lon1 - lon0) * w
        py = y + (lat0 - lat) / float(lat0 - lat1) * h
        return (int(px), int(py))

    for cont in CONTINENTS:
        pts = [proj(lo, la) for lo, la in cont]
        poly_fill(pts, LAND)
        poly_line(pts, INK, 1, close=True)
    # marker pins (small so the Berlin / The Hague / Kyiv cluster stays legible)
    for num, _label, lon, lat in MARKERS:
        mx, my = proj(lon, lat)
        circle(mx, my, 7, RED, fill=True)
        circle(mx, my, 7, WHITE)
        draw_text(mx - 2, my - 3, str(num), 1, WHITE)
    rect(x, y, w, h, INK, 2)


def draw_bar_chart(x, y, w, h):
    """GTA VI first-day sales (estimate) vs GTA V record, USD bn."""
    fill_rect(x, y, w, h, CREAM)
    draw_text(x + 6, y + 4, "FIRST-DAY SALES, $BN", 1, INK)
    base = y + h - 16
    hline(x + 4, x + w - 4, base, INK)
    # GTA V 2013: $0.80bn
    v_h = 16
    fill_rect(x + 14, base - v_h, 40, v_h, BLUE)
    draw_text(x + 34, base - v_h + 4, "0.80", 1, WHITE, align='c')
    draw_text(x + 34, base + 4, "GTA V 2013", 1, INK, align='c')
    # GTA VI 2026: ~$1.84bn (estimate)
    vi_h = 37
    fill_rect(x + 84, base - vi_h, 40, vi_h, RED)
    draw_text(x + 104, base - vi_h + 11, "1.84*", 1, WHITE, align='c')
    draw_text(x + 104, base + 4, "GTA VI 2026", 1, INK, align='c')
    rect(x, y, w, h, INK)


def draw_scales(x, y, w, h):
    """Mini scales of justice for the ICJ second lead."""
    fill_rect(x, y, w, h, CREAM)
    cx = x + w // 2
    top = y + 8
    line(cx, top, cx, y + h - 14, INK, 2)
    line(cx - 26, top + 6, cx + 26, top + 6, INK, 2)
    circle(cx, top, 3, INK, fill=True)
    for sgn in (-1, 1):
        px = cx + sgn * 26
        line(px, top + 6, px, top + 22, INK, 1)
        arc(px, top + 22, 10, 0, 180, INK, 1)
        line(px - 10, top + 22, px + 10, top + 22, INK, 1)
    line(cx - 12, y + h - 14, cx + 12, y + h - 14, INK, 2)
    draw_text(cx, y + h - 11, "9-6", 1, RED, align='c')
    rect(x, y, w, h, INK)


def draw_calendar(x, y, w, h):
    """Mini 2027 calendar page for the Trump / Iran second lead."""
    fill_rect(x, y, w, h, WHITE)
    fill_rect(x, y, w, 16, RED)
    draw_text(x + w // 2, y + 4, "2027", 1, WHITE, align='c')
    draw_text(x + w // 2, y + 26, "JAN", 2, INK, align='c')
    draw_text(x + w // 2, y + 44, "NO CALL", 1, INK, align='c')
    draw_text(x + w // 2, y + 54, "BEFORE", 1, INK, align='c')
    rect(x, y, w, h, INK)

# ---------------------------------------------------------------- content
# (number, text) -- research numbers 4..45; 1..3 are the featured stories.

REGIONS = [
    ("NORTH AMERICA", [
        (4, "White House press conference Friday after Trump returns from China."),
        (5, "Anthropic Nasdaq debut: priced $83, closed $97.17, +17%; value ~$2tn."),
        (6, "GTA VI first day: ~$1.84bn est., 19.1m copies (Sensor Tower); Take-Two unconfirmed."),
        (7, "Voyager 1 passes one light-day from Earth (25.9bn km); signal took a day."),
        (8, "US stocks end two-day rally on Fed rate worries; crude oil futures fall over 3%."),
    ]),
    ("LATIN AMERICA", [
        (9, "Lula, re-elected 25 Oct, in no hurry to name his next cabinet, Brasilia says."),
        (10, "Brazil Senate passes fiscal adjustment bill late Wednesday."),
        (11, "Venezuela's acting president Delcy Rodriguez tours Turkey, Qatar and UAE."),
    ]),
    ("EUROPE", [
        (12, "Berlin summit: Europe has 'a clear and consistent and united negotiating position'."),
        (13, "Kyiv: Russian drones kill 1, injure 5; Austrian and Dutch embassies damaged."),
        (14, "Putin invites Europeans to Moscow to clarify their Ukraine position."),
        (15, "Ukraine hits Crimean Bridge with Ruta missiles, reports say."),
        (16, "COP31 in Antalya: deadlock persists; states launch 'climate reality check'."),
        (17, "Spain heads to parliamentary elections on 29 Nov; Sanchez seeks re-election."),
    ]),
    ("MIDDLE EAST", [
        (18, "Houthi missile damages PIF Tower in Riyadh; windows blown out on 7-8 floors."),
        (19, "Coalition says it destroyed 4 ballistic missiles aimed at Saudi south."),
        (20, "Qatar, Kuwait and GCC condemn the Riyadh attack."),
        (21, "Israel's envoy: Israel may 'go it alone' against the Tehran regime."),
        (22, "Coalition strikes on Sanaa reported by Houthi-run Saba news agency."),
    ]),
    ("AFRICA", [
        (23, "DR Congo gives UN a week to fly out 750 South Sudanese fighters near Goma."),
        (24, "Sudan: RSF drone strikes widen against power grid; displaced return to Khartoum."),
        (25, "UAE sentences eight people to life over arms supplies to Sudan's army."),
        (26, "Ebola cases more than double in DR Congo, health officials report."),
        (27, "WHO Africa: AI helping reinforce polio surveillance across the region."),
    ]),
    ("ASIA-PACIFIC", [
        (28, "South Korea's top court overturns conviction of ex-PM Han Duck-soo in martial-law case."),
        (29, "Fiji declares national state of disaster over severe drought and water shortages."),
        (30, "Fire at ancestral home of ex-Bangladesh interim leader Muhammad Yunus; arson suspected."),
        (31, "Modi meets Prince and Princess of Wales in Delhi."),
        (32, "India signs Rs 1,976-crore defence deal with Israel Aerospace Industries for Navy Barak upgrade."),
        (33, "Sensex gains 1.21%, Nifty 1.14% on strong buying."),
        (34, "IAEA: North Korea expanding uranium enrichment at Yongbyon; 'serious concern', Grossi says."),
        (35, "APEC leaders discuss trade and tech in Shenzhen."),
        (36, "Trump-Xi-Putin trilateral in Shenzhen: 81 minutes, four-point declaration; 'a nuclear war cannot be won'."),
        (37, "Modi inaugurates FICCI centenary convention."),
    ]),
    ("SCIENCE, TECH & SPORT", [
        (38, "Hayabusa2: engine trouble forces JAXA probe to drop asteroid landing plan."),
        (39, "Nvidia chief Jensen Huang ousted amid espionage scandal, NYT revelations say."),
        (40, "GTA VI soundtrack album released today."),
        (41, "World Children's Day - observed today, 20 November."),
        (42, "Women's Asian Hockey Champions Trophy 2026 begins."),
        (43, "57th IFFI in Goa adds new animation section with five international films."),
        (44, "India v NZ, 1st Test: NZ 243/5 - Nicholls 113*, Phillips 94*; Bumrah 3-52."),
        (45, "Hong Kong Open badminton: India beat Malaysia."),
    ]),
]

WIRE = [
    ("00:01", "DR CONGO - UN FLY-OUT WEEK"),
    ("00:05", "SUDAN - RSF DRONE STRIKES"),
    ("00:08", "GULF CONDEMNS RIYADH HIT"),
    ("00:18", "PIF TOWER DAMAGE CONFIRMED"),
    ("01:19+03", "TRUMP DEFERS IRAN CALL"),
    ("01:30", "HAYABUSA2 DROPS LANDING"),
    ("01:43", "300,000 EVACUATED: THE HINDU"),
    ("03:06", "REUTERS: TRUMP ON IRAN"),
    ("06:30", "AKVAN LANDFALL"),
    ("23:50*", "VOYAGER 1: ONE LIGHT-DAY"),
]

LEAD_DECK = (
    "Severe Cyclonic Storm Akvan crosses the north Andhra Pradesh-Yanam "
    "and south Odisha coasts around noon IST (06:30 UTC), with winds "
    "90-100 km/h gusting 110. Odisha has moved 300,000+ people to safety; "
    "423 rescue teams are deployed, 69 trains cancelled, red alerts in "
    "six districts. Third cyclone on this coast in a month, after Arnab "
    "and Murasu. (IMD via India Today/PTI; The Hindu)"
)

LEAD_FACTS = [
    "300,000+ EVACUATED IN ODISHA",
    "423 RESCUE TEAMS DEPLOYED",
    "20-30 CM RAIN - FLASH-FLOOD RISK",
]

TRUMP_TEXT = (
    "Trump told Axios, by phone from Air Force One returning from China: "
    "'I am not rushing into any decision... We will see what happens "
    "after the beginning of the year.' No new US strikes on Iran before "
    "2027; Israel's envoy says Israel may 'go it alone'."
)

ICJ_TEXT = (
    "The Hague, 19 Nov: by 9 votes to 6, the court held Myanmar "
    "responsible for genocide against the Rohingya - the first time in "
    "the ICJ's 80-year history a state has been held responsible. "
    "10,000 killed in 2017; reparations ordered. Final and binding; "
    "no enforcement power."
)


def section_rule(y, color=INK, t=2):
    hline(16, W - 16, y, color, t)


def draw_region_column(x, y, w, title, items, max_y, gap=3, leading=8):
    """One region column; returns bottom y. Warns on overflow."""
    fill_rect(x, y, w, 13, INK)
    draw_text(x + 4, y + 3, title + " (" + str(len(items)) + ")", 1, WHITE)
    cy = y + 17
    for num, text in items:
        full = str(num) + ". " + text
        lines = wrap_text(full, w, 1)
        if len(lines) > 3:
            print("WARN: brief %d wraps to %d lines" % (num, len(lines)))
        for i, ln in enumerate(lines):
            if i == 0:
                # red story number, rest of line in ink
                npre = str(num) + ". "
                draw_text(x, cy, npre, 1, RED)
                draw_text(x + text_w(npre, 1), cy, ln[len(npre):], 1, INK)
            else:
                draw_text(x, cy, ln, 1, INK)
            cy += leading
        cy += gap
    if cy > max_y:
        print("WARN: column %s ends y=%d > max_y=%d" % (title, cy, max_y))
    else:
        print("OK: column %s ends y=%d (max %d)" % (title, cy, max_y))
    return cy


def draw_masthead():
    fill_rect(0, 0, W, 26, BLACK)
    draw_text(16, 9, "FRIDAY 20 NOVEMBER 2026", 1, WHITE)
    draw_text(W // 2, 9, "45 STORIES - 7 REGIONS - ONE IMAGE", 1, WHITE,
              align='c')
    draw_text(W - 16, 9, "FRIDAY EDITION - NO. 324", 1, WHITE, align='r')
    draw_text(W // 2, 34, "THE WORLD DISPATCH", 7, INK, align='c')
    draw_text(W // 2, 88, "THE DAY'S WORLD NEWS - VERIFIED, NUMBERED, IN ONE PAGE",
              1, GREY, align='c')
    section_rule(100)
    idx = ("INSIDE: 1 AKVAN LANDFALL  2 TRUMP DEFERS IRAN CALL  "
           "3 ICJ: MYANMAR GUILTY  4 ANTHROPIC $2TN DEBUT  "
           "5 GTA VI $1.84BN*  6 VOYAGER 1 A LIGHT-DAY AWAY  "
           "7 BERLIN UKRAINE TALKS  8 RIYADH MISSILE  "
           "9 DR CONGO FLY-OUT  10 TRUMP-XI-PUTIN SUMMIT")
    text_block(16, 105, idx, W - 32, 1, INK, leading=9, max_lines=2)
    section_rule(124)


def draw_lead():
    y = 128
    # left text column
    draw_text(16, y + 4, "LEAD - INDIA - CYCLONE", 1, RED)
    draw_text(16, y + 16, "AKVAN SLAMS", 4, INK)
    draw_text(16, y + 44, "INDIAN COAST", 4, RED)
    nlines = len(wrap_text(LEAD_DECK, 322, 1))
    text_block(16, y + 76, LEAD_DECK, 322, 1, INK, leading=9)
    fy = y + 76 + nlines * 9 + 6
    for fact in LEAD_FACTS:
        fill_rect(16, fy + 1, 5, 5, RED)
        draw_text(26, fy, fact, 1, INK)
        fy += 10
    # right art panel
    draw_cyclone(348, y, 660, 180)
    section_rule(314)


def draw_second_leads():
    y = 320
    # left: Trump / Iran
    fill_rect(16, y, 490, 98, CREAM)
    rect(16, y, 490, 98, INK)
    draw_text(26, y + 6, "WASHINGTON - 20 NOV", 1, RED)
    draw_text(26, y + 17, "TRUMP DEFERS IRAN", 2, INK)
    draw_text(26, y + 31, "DECISION TO 2027", 2, INK)
    text_block(26, y + 48, TRUMP_TEXT, 392, 1, INK, leading=9)
    draw_calendar(432, y + 12, 62, 74)
    # right: ICJ / Myanmar
    fill_rect(518, y, 490, 98, CREAM)
    rect(518, y, 490, 98, INK)
    draw_text(528, y + 6, "THE HAGUE - THURSDAY 19 NOVEMBER", 1, RED)
    draw_text(528, y + 17, "ICJ: MYANMAR GUILTY", 2, INK)
    draw_text(528, y + 31, "OF GENOCIDE", 2, RED)
    text_block(528, y + 48, ICJ_TEXT, 392, 1, INK, leading=9)
    draw_scales(934, y + 12, 62, 74)
    section_rule(424)


def draw_map_strip():
    y = 430
    draw_text(16, y, "THE WORLD AT A GLANCE - 8 MARKERS", 1, INK)
    draw_text(W - 16, y, "NUMBERS MATCH THE STORY LIST", 1, GREY, align='r')
    draw_map(16, y + 12, 620, 96)
    lx = 652
    ly = y + 12
    for num, label, _lon, _lat in MARKERS:
        circle(lx + 7, ly + 4, 7, RED, fill=True)
        draw_text(lx + 5, ly + 1, str(num), 1, WHITE)
        draw_text(lx + 18, ly + 1, label, 1, INK)
        ly += 11
    draw_text(lx, ly + 1, "MAP: SIMPLIFIED OUTLINES", 1, GREY)
    section_rule(540)


def draw_wire():
    y = 546
    draw_text(16, y, "THE WIRE - ALL TIMES UTC", 1, INK)
    draw_text(16, y + 11, "*19 NOV 23:50 UTC", 1, GREY)
    # two columns of five timed items
    for i, (t, label) in enumerate(WIRE):
        col = i // 5
        row = i % 5
        ix = 16 + col * 305
        iy = y + 22 + row * 9
        draw_text(ix, iy, t, 1, RED)
        draw_text(ix + 56, iy, label, 1, INK)
    # bar chart + markets on the right
    draw_bar_chart(640, y, 168, 62)
    mx = 820
    fill_rect(mx, y, 188, 62, WHITE)
    rect(mx, y, 188, 62, INK)
    draw_text(mx + 6, y + 4, "MARKETS", 1, INK)
    draw_text(mx + 6, y + 15, "SENSEX +1.21%  NIFTY +1.14%", 1, INK)
    draw_text(mx + 6, y + 26, "ANTHROPIC $97.17  +17%", 1, INK)
    draw_text(mx + 6, y + 37, "CRUDE OIL FUTURES -3%+", 1, INK)
    draw_text(mx + 6, y + 48, "GTA VI 19.1M COPIES*", 1, GREY)
    section_rule(616)

# ---------------------------------------------------------------- page

def draw_regions():
    # band 1: four columns (North America, Latin America, Europe, Middle East)
    y = 622
    cols1 = [(16, 242), (266, 242), (516, 242), (766, 242)]
    for (cx, cw), (title, items) in zip(cols1, REGIONS[:4]):
        draw_region_column(cx, y, cw, title, items, 812)
    section_rule(818)
    # band 2: three columns (Africa, Asia-Pacific, Science/Tech/Sport)
    y = 824
    cols2 = [(16, 325), (349, 325), (682, 325)]
    for (cx, cw), (title, items) in zip(cols2, REGIONS[4:]):
        draw_region_column(cx, y, cw, title, items, 994, gap=2)


def draw_footer():
    section_rule(1000)
    foot = ("SOURCES: IMD, REUTERS, BBC, CNN, AFP, THE HINDU, NASA/JPL, IAEA, "
            "UN NEWS, LE MONDE - ALL FIGURES FROM NAMED SOURCES; * = ESTIMATE "
            "(SENSOR TOWER; TAKE-TWO UNCONFIRMED) - ICJ RULING IS A 19 NOV EVENT - "
            "45 STORIES - 7 REGIONS - THE WORLD DISPATCH, FRIDAY 20 NOVEMBER 2026")
    text_block(16, 1005, foot, W - 32, 1, GREY, leading=9)


def grain(amount=1):
    """Deterministic sparse luminance grain over the whole page (adds
    print texture; also keeps the PNG honestly dense)."""
    for yy in range(H):
        base = yy * W * 3
        for xx in range(W):
            h = (xx * 374761393 + yy * 668265263) & 0xFFFFFFFF
            h ^= h >> 13
            h = (h * 1274126177) & 0xFFFFFFFF
            h ^= h >> 16
            if h % 6 != 0:
                continue
            d = 1 if (h >> 8) % 2 else -1
            i = base + xx * 3
            for k in range(3):
                v = _px[i + k] + d
                _px[i + k] = 0 if v < 0 else (255 if v > 255 else v)


def build_page():
    fill_rect(0, 0, W, H, PAPER)
    speckle(0, 0, W, H, (233, 227, 212), density=2600)
    speckle(0, 0, W, H, (255, 250, 238), density=1600)
    draw_masthead()
    draw_lead()
    draw_second_leads()
    draw_map_strip()
    draw_wire()
    draw_regions()
    draw_footer()
    grain(1)


# ---------------------------------------------------------------- PNG

def _chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    out += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    for yy in range(H):
        raw.append(0)
        raw += _px[yy * W * 3:(yy + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 6)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", comp)
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    build_page()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    size = write_png(path)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
