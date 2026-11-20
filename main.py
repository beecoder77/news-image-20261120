#!/usr/bin/env python3
"""news-image-20261120 v3 — classic newspaper front page.

Fresh, stdlib-only renderer (math/os/struct/zlib). All copy is original
wording written for this entry from research-20nov.md; layout follows the
classic front-page structure (masthead, stat strip, 3 illustrated leads,
10 numbered mid stories, numbered world map, 23-item list, date-check box).
Deterministic: running twice produces a byte-identical entry.png.
"""
import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 240, 220)
PANEL = (250, 246, 232)
INK = (30, 28, 25)
RED = (176, 30, 40)
NAVY = (28, 52, 88)
SEA = (34, 58, 92)
LAND = (233, 221, 190)
LAND_EDGE = (120, 108, 82)
GREY = (96, 90, 78)
RULE = (70, 62, 48)
SKY = (206, 222, 230)
SEA2 = (158, 190, 204)
GOLD = (196, 138, 30)
BROWN = (122, 90, 58)

# ---------------------------------------------------------------- framebuffer
fb = bytearray(W * H * 3)


def _clamp(v):
    return 0 if v < 0 else (255 if v > 255 else v)


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        fb[i] = c[0]
        fb[i + 1] = c[1]
        fb[i + 2] = c[2]


def fill_rect(x, y, w, h, c):
    x0 = max(0, int(x))
    y0 = max(0, int(y))
    x1 = min(W, int(x + w))
    y1 = min(H, int(y + h))
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            fb[i] = c[0]
            fb[i + 1] = c[1]
            fb[i + 2] = c[2]


def hline(x, y, w, c, t=1):
    fill_rect(x, y, w, t, c)


def vline(x, y, h, c, t=1):
    fill_rect(x, y, t, h, c)


def rect_outline(x, y, w, h, c, t=1):
    hline(x, y, w, c, t)
    hline(x, y + h - t, w, c, t)
    vline(x, y, h, c, t)
    vline(x + w - t, y, h, c, t)


def draw_line(x0, y0, x1, y1, c):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        px(x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_line_w(x0, y0, x1, y1, c, w=2):
    for k in range(-(w // 2), w // 2 + 1):
        draw_line(x0, y0 + k, x1, y1 + k, c)


def fill_circle(cx, cy, r, c):
    cx, cy, r = int(cx), int(cy), int(r)
    for yy in range(cy - r, cy + r + 1):
        dx = int(math.sqrt(max(0, r * r - (yy - cy) ** 2)))
        for xx in range(cx - dx, cx + dx + 1):
            px(xx, yy, c)


def circle_outline(cx, cy, r, c):
    cx, cy, r = int(cx), int(cy), int(r)
    steps = max(24, int(2 * math.pi * r))
    for k in range(steps):
        a = 2 * math.pi * k / steps
        px(int(cx + r * math.cos(a)), int(cy + r * math.sin(a)), c)


def fill_poly(points, c):
    """Scanline polygon fill. points: list of (x, y) in float/int."""
    if len(points) < 3:
        return
    pts = [(float(x), float(y)) for x, y in points]
    ymin = int(math.ceil(min(p[1] for p in pts)))
    ymax = int(math.floor(max(p[1] for p in pts)))
    n = len(pts)
    for y in range(ymin, ymax + 1):
        xs = []
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(int(math.ceil(xs[k])), int(math.floor(xs[k + 1])) + 1):
                px(x, y, c)


def poly_outline(points, c):
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        draw_line(x0, y0, x1, y1, c)


# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 chars, '#' = ink, '.' = blank. Authored here.
def _g(*rows):
    return rows


FONT = {
    'A': _g("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': _g("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': _g("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': _g("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': _g("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': _g("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': _g("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': _g("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': _g("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': _g("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': _g("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': _g("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': _g("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': _g("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': _g("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': _g("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': _g("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': _g("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': _g("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': _g("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': _g("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': _g("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': _g("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': _g("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': _g("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': _g("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    'a': _g("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    'b': _g("10000", "10000", "10110", "11001", "10001", "10001", "11110"),
    'c': _g("00000", "00000", "01110", "10001", "10000", "10001", "01110"),
    'd': _g("00001", "00001", "01101", "10011", "10001", "10001", "01111"),
    'e': _g("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    'f': _g("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    'g': _g("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    'h': _g("10000", "10000", "10110", "11001", "10001", "10001", "10001"),
    'i': _g("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    'j': _g("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    'k': _g("10000", "10000", "10010", "10100", "11000", "10100", "10001"),
    'l': _g("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    'm': _g("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    'n': _g("00000", "00000", "10110", "11001", "10001", "10001", "10001"),
    'o': _g("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    'p': _g("00000", "00000", "10110", "11001", "10001", "11110", "10000"),
    'q': _g("00000", "00000", "01101", "10011", "10001", "01111", "00001"),
    'r': _g("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    's': _g("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    't': _g("01000", "01000", "11100", "01000", "01000", "01001", "00110"),
    'u': _g("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    'v': _g("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    'w': _g("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    'x': _g("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    'y': _g("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    'z': _g("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    '0': _g("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': _g("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': _g("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': _g("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': _g("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': _g("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': _g("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': _g("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': _g("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': _g("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': _g("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': _g("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': _g("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ':': _g("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': _g("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    '!': _g("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': _g("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": _g("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': _g("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    '-': _g("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '(': _g("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': _g("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '/': _g("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '%': _g("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '+': _g("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '=': _g("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '&': _g("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '$': _g("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '*': _g("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    '#': _g("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    '@': _g("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    '\u00b7': _g("00000", "00000", "00000", "01100", "01100", "00000", "00000"),
    '\u2014': _g("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    '\u2013': _g("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '\u2019': _g("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '\u201c': _g("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    '\u201d': _g("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    '\u00b0': _g("01100", "10010", "10010", "01100", "00000", "00000", "00000"),
}

_MISSING = FONT['?']


def text_w(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(x, y, s, scale, c):
    x = int(x)
    y = int(y)
    for ch in s:
        glyph = FONT.get(ch, _MISSING)
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '1':
                    fill_rect(x + col * scale, y + row * scale, scale, scale, c)
        x += 6 * scale


def draw_text_centered(cx, y, s, scale, c):
    draw_text(cx - text_w(s, scale) // 2, y, s, scale, c)


def wrap_text(s, width_px, scale):
    """Greedy word wrap; returns list of lines, each fits width_px."""
    max_chars = max(1, width_px // (6 * scale))
    words = s.split(' ')
    lines = []
    cur = ''
    for w in words:
        cand = w if not cur else cur + ' ' + w
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            # hard-split a single overlong word
            while len(w) > max_chars:
                lines.append(w[:max_chars])
                w = w[max_chars:]
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_para(x, y, s, width_px, scale, c, leading=2):
    lines = wrap_text(s, width_px, scale)
    for i, ln in enumerate(lines):
        draw_text(x, y + i * (7 * scale + leading), ln, scale, c)
    return len(lines)


# ---------------------------------------------------------------- PNG output
def save_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += fb[y * W * 3:(y + 1) * W * 3]

    def chunk(typ, data):
        return (struct.pack('>I', len(data)) + typ + data +
                struct.pack('>I', zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
           chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)
    return len(png)


def paper_grain():
    """Deterministic newsprint grain on the bare paper/panel areas only,
    so text and drawings stay crisp while the page feels like newsprint
    (and the PNG carries the texture of a scanned front page)."""
    for y in range(H):
        base = y * W * 3
        for x in range(W):
            i = base + x * 3
            if ((fb[i] == PAPER[0] and fb[i + 1] == PAPER[1]
                 and fb[i + 2] == PAPER[2])
                    or (fb[i] == PANEL[0] and fb[i + 1] == PANEL[1]
                        and fb[i + 2] == PANEL[2])):
                h = ((x // 2) * 2654435761 + (y // 2) * 40503) & 0xFFFFFFFF
                h ^= h >> 16
                d = (h % 5) - 2
                fb[i] = _clamp(fb[i] + d)
                fb[i + 1] = _clamp(fb[i + 1] + d)
                fb[i + 2] = _clamp(fb[i + 2] + d)

# ---------------------------------------------------------------- illustrations
# All drawings are original vector-style scenes made from the primitives above.

def ill_cyclone(x, y, w, h):
    fill_rect(x, y, w, h, SKY)
    fill_rect(x, y + h - 20, w, 20, SEA2)
    hline(x, y + h - 20, w, NAVY)
    # spiral storm: Archimedean spiral, dark navy, double stroke
    cx, cy = x + w // 3, y + h // 2 - 4
    pts = []
    for k in range(0, 200):
        t = k / 200.0 * 4.2 * math.pi
        r = 2 + t * 2.6
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t) * 0.85))
    for k in range(len(pts) - 1):
        draw_line(pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1], NAVY)
        draw_line(pts[k][0], pts[k][1] + 1, pts[k + 1][0], pts[k + 1][1] + 1, NAVY)
    fill_circle(cx, cy, 3, PAPER)
    # rain slashes on the right
    for k in range(9):
        rx = x + w - 110 + k * 11
        ry = y + 8 + (k % 3) * 14
        draw_line(rx, ry, rx - 5, ry + 9, NAVY)
    # two small houses on the coast, left
    for hx in (x + 8, x + 52):
        hy = y + h - 34
        fill_rect(hx, hy, 26, 14, (238, 228, 200))
        fill_poly([(hx - 3, hy), (hx + 13, hy - 10), (hx + 29, hy)], BROWN)
        fill_rect(hx + 10, hy + 6, 6, 8, INK)
    # wind chevrons
    for k in range(3):
        wx = x + w - 46 + k * 12
        wy = y + h - 14
        draw_line(wx, wy, wx + 6, wy - 4, RED)
        draw_line(wx, wy, wx + 6, wy + 4, RED)


def ill_podium(x, y, w, h):
    fill_rect(x, y, w, h, (240, 232, 214))
    # flag poles
    for fx, stripes in ((x + 26, True), (x + w - 46, False)):
        vline(fx, y + 8, 40, INK, 2)
        if stripes:
            for s in range(4):
                fill_rect(fx + 2, y + 8 + s * 5, 26, 3,
                          RED if s % 2 == 0 else PAPER)
            fill_rect(fx + 2, y + 8, 12, 8, NAVY)
        else:
            fill_rect(fx + 2, y + 8, 26, 6, (0, 122, 61))
            fill_rect(fx + 2, y + 14, 26, 6, PAPER)
            fill_rect(fx + 2, y + 20, 26, 6, RED)
    # podium
    fill_poly([(x + w // 2 - 52, y + h - 8), (x + w // 2 - 40, y + 34),
               (x + w // 2 + 40, y + 34), (x + w // 2 + 52, y + h - 8)], BROWN)
    hline(x + w // 2 - 40, y + 34, 80, INK)
    # microphone
    draw_line(x + w // 2 - 12, y + 34, x + w // 2 - 4, y + 18, INK)
    fill_circle(x + w // 2 - 3, y + 16, 4, INK)
    # paper sheet on the podium reading 2027
    fill_rect(x + w // 2 - 16, y + h - 34, 32, 22, PAPER)
    rect_outline(x + w // 2 - 16, y + h - 34, 32, 22, INK)
    draw_text(x + w // 2 - 12, y + h - 28, "2027", 1, INK)


def ill_chart(x, y, w, h):
    fill_rect(x, y, w, h, (238, 234, 220))
    base = y + h - 12
    bars = [(26, 16), (30, 26), (34, 38), (40, 52)]
    bx = x + 30
    for bw, bh in bars:
        fill_rect(bx, base - bh, bw, bh, NAVY)
        bx += bw + 18
    # last bar in red to mark the close
    fill_rect(bx - 18 - 40, base - 52, 40, 52, RED)
    hline(x + 14, base, w - 28, INK, 2)
    # rising arrow
    ax = [x + 44, x + 96, x + 150, x + 208, x + 262]
    ay = [base - 22, base - 34, base - 46, base - 58, base - 70]
    for k in range(len(ax) - 1):
        draw_line_w(ax[k], ay[k], ax[k + 1], ay[k + 1], RED, 2)
    fill_poly([(ax[-1], ay[-1]), (ax[-1] - 12, ay[-1] + 2),
               (ax[-1] - 2, ay[-1] + 12)], RED)
    draw_text(x + w - 78, y + 6, "+17%", 1, RED)


# ---- small mid-story icons (40 x 30 box) ----

def ic_car(x, y):
    fill_poly([(x + 3, y + 21), (x + 7, y + 14), (x + 15, y + 12),
               (x + 25, y + 12), (x + 31, y + 15), (x + 36, y + 21)], NAVY)
    fill_rect(x + 9, y + 14, 7, 5, SKY)
    fill_rect(x + 18, y + 14, 7, 5, SKY)
    fill_circle(x + 11, y + 22, 4, INK)
    fill_circle(x + 28, y + 22, 4, INK)
    fill_circle(x + 11, y + 22, 2, PAPER)
    fill_circle(x + 28, y + 22, 2, PAPER)


def ic_plane(x, y):
    draw_line_w(x + 4, y + 16, x + 36, y + 16, NAVY, 2)
    fill_poly([(x + 17, y + 16), (x + 23, y + 7), (x + 27, y + 7),
               (x + 22, y + 16)], NAVY)
    fill_poly([(x + 6, y + 16), (x + 4, y + 9), (x + 8, y + 9),
               (x + 11, y + 16)], NAVY)
    fill_poly([(x + 33, y + 16), (x + 36, y + 12), (x + 37, y + 15),
               (x + 35, y + 17)], RED)


def ic_bolt(x, y):
    fill_poly([(x + 22, y + 3), (x + 11, y + 17), (x + 17, y + 17),
               (x + 13, y + 28), (x + 26, y + 13), (x + 20, y + 13)], GOLD)


def ic_scales(x, y):
    vline(x + 20, y + 5, 20, INK, 2)
    hline(x + 8, y + 6, 24, INK, 2)
    fill_circle(x + 20, y + 5, 2, INK)
    for cx in (x + 9, x + 31):
        draw_line(cx, y + 7, cx - 5, y + 16, INK)
        draw_line(cx, y + 7, cx + 5, y + 16, INK)
        hline(cx - 5, y + 16, 11, INK, 2)
    hline(x + 12, y + 26, 16, INK, 2)


def ic_globe(x, y):
    circle_outline(x + 20, y + 15, 11, NAVY)
    draw_line(x + 20, y + 4, x + 20, y + 26, NAVY)
    hline(x + 9, y + 15, 22, NAVY)
    draw_line(x + 11, y + 8, x + 29, y + 22, NAVY)
    draw_line(x + 29, y + 8, x + 11, y + 22, NAVY)


def ic_satellite(x, y):
    fill_rect(x + 16, y + 12, 9, 7, NAVY)
    fill_rect(x + 5, y + 13, 9, 5, (150, 160, 175))
    fill_rect(x + 27, y + 13, 9, 5, (150, 160, 175))
    draw_line(x + 20, y + 12, x + 14, y + 5, INK)
    fill_circle(x + 13, y + 4, 2, RED)
    fill_circle(x + 33, y + 24, 4, GREY)
    fill_circle(x + 34, y + 23, 1, INK)


def ic_star(x, y):
    fill_poly([(x + 14, y + 3), (x + 17, y + 10), (x + 24, y + 11),
               (x + 18, y + 16), (x + 20, y + 23), (x + 14, y + 19),
               (x + 8, y + 23), (x + 10, y + 16), (x + 4, y + 11),
               (x + 11, y + 10)], GOLD)
    for k in range(4):
        fill_circle(x + 26 + k * 3, y + 22 + k, 1, NAVY)


def ic_bat(x, y):
    fill_poly([(x + 9, y + 26), (x + 13, y + 22), (x + 23, y + 7),
               (x + 27, y + 9), (x + 17, y + 24), (x + 13, y + 27)], BROWN)
    draw_line(x + 23, y + 7, x + 28, y + 2, BROWN)
    draw_line_w(x + 23, y + 7, x + 28, y + 2, BROWN, 2)
    fill_circle(x + 31, y + 20, 4, RED)
    fill_circle(x + 30, y + 19, 1, PAPER)


def ic_balloon(x, y):
    fill_circle(x + 19, y + 10, 8, RED)
    fill_poly([(x + 16, y + 18), (x + 22, y + 18), (x + 19, y + 22)], RED)
    draw_line(x + 19, y + 22, x + 16, y + 26, INK)
    draw_line(x + 16, y + 26, x + 21, y + 28, INK)


def ic_megaphone(x, y):
    fill_poly([(x + 7, y + 13), (x + 26, y + 6), (x + 26, y + 22),
               (x + 7, y + 17)], NAVY)
    fill_rect(x + 9, y + 17, 5, 8, NAVY)
    for r in (4, 8):
        px(x + 31, y + 12, RED)
        circle_outline(x + 26, y + 14, r, RED)


ICONS = {4: ic_car, 5: ic_plane, 6: ic_bolt, 7: ic_scales, 8: ic_globe,
         9: ic_satellite, 10: ic_star, 11: ic_bat, 12: ic_balloon,
         13: ic_megaphone}

# ---------------------------------------------------------------- world map
# Coarse continent outlines as (lon, lat) points; stylised, recognisable.
NORTH_AMERICA = [(-168, 66), (-166, 60), (-158, 58), (-153, 58), (-146, 60),
                 (-140, 60), (-135, 58), (-130, 54), (-126, 50), (-124, 44),
                 (-122, 38), (-120, 34), (-116, 32), (-112, 29), (-109, 25),
                 (-106, 22), (-102, 18), (-97, 16), (-94, 17), (-91, 14),
                 (-88, 13), (-85, 12), (-83, 9), (-80, 8), (-78, 8),
                 (-80, 9), (-83, 10), (-86, 12), (-88, 14), (-91, 15),
                 (-95, 16), (-97, 18), (-97, 22), (-97, 26), (-94, 29),
                 (-91, 29), (-88, 30), (-85, 30), (-82, 28), (-81, 25),
                 (-80, 31), (-78, 34), (-76, 36), (-74, 39), (-71, 41),
                 (-69, 44), (-66, 45), (-61, 46), (-56, 47), (-60, 50),
                 (-64, 55), (-66, 58), (-70, 58), (-76, 62), (-82, 64),
                 (-88, 66), (-94, 68), (-100, 69), (-108, 68), (-116, 69),
                 (-124, 70), (-132, 70), (-140, 70), (-148, 71), (-156, 71),
                 (-163, 70), (-168, 66)]
SOUTH_AMERICA = [(-79, 9), (-77, 5), (-78, 1), (-80, -3), (-81, -6),
                 (-79, -9), (-76, -13), (-73, -17), (-71, -20), (-70, -24),
                 (-70, -30), (-71, -33), (-73, -38), (-73, -44), (-74, -49),
                 (-73, -52), (-70, -54), (-67, -55), (-65, -51), (-66, -46),
                 (-65, -42), (-62, -39), (-58, -36), (-54, -34), (-50, -30),
                 (-47, -26), (-42, -23), (-40, -20), (-38, -16), (-36, -11),
                 (-35, -7), (-36, -4), (-40, -3), (-43, -2), (-47, -1),
                 (-50, 0), (-53, 2), (-56, 4), (-59, 7), (-62, 9),
                 (-66, 10), (-70, 11), (-73, 11), (-76, 10), (-79, 9)]
AFRICA = [(-6, 35), (-10, 31), (-15, 28), (-17, 21), (-17, 15), (-16, 12),
          (-13, 8), (-9, 5), (-5, 5), (0, 6), (5, 4), (9, 4), (12, 0),
          (12, -5), (13, -10), (12, -15), (13, -18), (15, -22), (16, -28),
          (18, -33), (20, -35), (26, -34), (30, -31), (33, -27), (36, -24),
          (39, -20), (40, -15), (40, -10), (41, -6), (43, -2), (46, -1),
          (51, 2), (51, 11), (48, 11), (44, 11), (41, 13), (39, 16),
          (37, 19), (36, 22), (34, 27), (32, 31), (29, 31), (25, 32),
          (21, 33), (18, 33), (15, 33), (11, 34), (10, 37), (6, 37),
          (0, 36), (-6, 35)]
EURASIA = [(-9, 37), (-9, 43), (-2, 44), (-1, 46), (-4, 48), (-1, 49),
           (2, 51), (5, 53), (8, 55), (8, 57), (11, 59), (6, 58), (5, 60),
           (9, 62), (13, 66), (18, 69), (22, 70), (28, 71), (32, 70),
           (38, 68), (44, 68), (50, 69), (56, 68), (63, 69), (68, 70),
           (73, 72), (78, 73), (84, 74), (90, 75), (96, 76), (102, 77),
           (108, 75), (113, 73), (118, 73), (124, 73), (130, 72), (136, 72),
           (142, 72), (148, 71), (154, 70), (158, 69), (162, 68), (168, 66),
           (174, 65), (178, 65), (178, 62), (170, 60), (162, 60), (158, 52),
           (156, 51), (150, 59), (142, 59), (141, 53), (140, 48), (138, 45),
           (135, 43), (132, 42), (130, 39), (127, 35), (126, 33), (127, 31),
           (122, 31), (121, 28), (119, 25), (116, 23), (112, 21), (109, 18),
           (107, 11), (105, 9), (103, 7), (101, 6), (99, 8), (98, 11),
           (97, 15), (94, 17), (92, 21), (90, 22), (88, 22), (86, 20),
           (83, 18), (80, 15), (80, 13), (77, 8), (76, 10), (74, 14),
           (72, 20), (69, 22), (66, 25), (62, 25), (58, 25), (56, 26),
           (54, 26), (52, 25), (50, 26), (50, 29), (48, 30), (44, 31),
           (40, 32), (36, 36), (33, 36), (30, 36), (27, 37), (23, 36),
           (19, 40), (15, 40), (12, 44), (8, 44), (3, 43), (0, 39),
           (-2, 37), (-6, 36), (-9, 37)]
AUSTRALIA = [(113, -22), (114, -30), (115, -35), (118, -35), (124, -33),
             (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
             (145, -38), (150, -37), (153, -32), (153, -27), (150, -23),
             (146, -19), (143, -15), (142, -11), (141, -13), (139, -17),
             (136, -15), (135, -12), (132, -11), (130, -13), (127, -14),
             (124, -15), (122, -17), (118, -20), (115, -21), (113, -22)]
GREENLAND = [(-45, 60), (-40, 64), (-32, 68), (-25, 70), (-20, 70),
             (-22, 74), (-30, 76), (-40, 76), (-50, 75), (-58, 74),
             (-55, 70), (-52, 64), (-48, 61), (-45, 60)]
UK = [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51),
      (-3, 50), (-5, 50)]
JAPAN = [(130, 31), (132, 33), (134, 34), (137, 35), (139, 35), (140, 38),
         (141, 40), (142, 42), (144, 44), (143, 42), (141, 39), (139, 37),
         (137, 36), (135, 34), (133, 33), (131, 32), (130, 31)]
NEW_ZEALAND = [(167, -45), (170, -43), (173, -41), (175, -38), (177, -38),
               (176, -40), (174, -42), (172, -43), (169, -46), (167, -45)]
MADAGASCAR = [(44, -16), (47, -15), (50, -16), (49, -20), (47, -24),
              (44, -25), (43, -21), (43, -17), (44, -16)]
BORNEO = [(109, 1), (113, 4), (117, 6), (119, 1), (118, -3), (114, -4),
          (110, -3), (109, 1)]
SUMATRA = [(95, 5), (98, 3), (101, 0), (104, -3), (106, -6), (103, -5),
           (100, -1), (97, 3), (95, 5)]
NEW_GUINEA = [(131, -1), (136, -3), (141, -4), (146, -7), (150, -9),
              (146, -8), (141, -8), (136, -6), (132, -4), (131, -1)]
CONTINENTS = [NORTH_AMERICA, SOUTH_AMERICA, AFRICA, EURASIA, AUSTRALIA,
              GREENLAND, UK, JAPAN, NEW_ZEALAND, MADAGASCAR, BORNEO,
              SUMATRA, NEW_GUINEA]

# marker number -> (lon, lat) for featured stories 1-13
MARKERS = {1: (85, 20), 2: (-77, 39), 3: (-74, 41), 4: (-122, 37),
           5: (29, -1.5), 6: (32.5, 15.6), 7: (54.4, 24.5), 8: (30.7, 36.9),
           9: (139.7, 35.7), 10: (-150, -20), 11: (174.8, -41.3),
           12: (6, 46), 13: (46.7, 24.6)}
MARKER_PLACE = {1: "Odisha", 2: "Washington", 3: "New York",
                4: "San Francisco", 5: "Goma", 6: "Khartoum",
                7: "Abu Dhabi", 8: "Antalya", 9: "Tokyo",
                10: "Deep space", 11: "Wellington", 12: "Geneva",
                13: "Riyadh"}

# ---------------------------------------------------------------- content
# All wording is original, written for this entry from research-20nov.md.

CHIPS = [("EUROPE", 5), ("THE AMERICAS", 8), ("ASIA-PACIFIC", 11),
         ("MIDEAST", 4), ("AFRICA", 4), ("OCEANIA", 1), ("WORLD", 3)]

STATS = [
    ("300,000", "people evacuated in Odisha"),
    ("$97.17", "Anthropic first close, +17%"),
    ("118*", "Nicholls not out, Wellington"),
    ("423", "rescue teams in Odisha"),
    ("750", "fighters to be flown out of Congo"),
    ("19.1m", "GTA VI copies, day one (est.)"),
]

LEADS = [
    ("AKVAN SLAMS INTO",
     "ODISHA AT NOON",
     "Severe Cyclone Akvan crosses the Odisha coast near Gopalpur around "
     "noon, with winds of 90-100 km/h gusting to 110. More than 300,000 "
     "people have been moved to safety and 423 rescue teams are deployed. "
     "Six districts are on red alert and 69 trains are cancelled. It is "
     "the third cyclone here in a month.",
     ill_cyclone),
    ("TRUMP: NO IRAN",
     "DECISION BEFORE 2027",
     "President Trump says he is in no rush on Iran, telling Axios from Air "
     "Force One that no decision will come before the new year. There will "
     "be no new US strikes on Iran before 2027. Israel's envoy in "
     "Washington says Israel may act alone against Tehran.",
     ill_podium),
    ("ANTHROPIC SOARS ON",
     "$2TN DEBUT",
     "Anthropic shares closed their first day at $97.17, up 17% on the $83 "
     "issue price, valuing the AI firm at about $2 trillion. The $81.3bn "
     "float is the largest IPO on record. Trading began on Thursday in "
     "New York.",
     ill_chart),
]

MIDS = [
    (4, "GTA VI SELLS 19.1M ON DAY ONE",
     "Sensor Tower estimates day-one sales near $1.84bn, over twice GTA V's "
     "$800m record. Take-Two has not confirmed the figures."),
    (5, "CONGO: UN GIVEN WEEK TO FLY OUT 750",
     "Fighters loyal to sacked vice-president Riek Machar, disarmed and held "
     "in UN camps near Goma, must be flown out within a week."),
    (6, "SUDAN GRID HIT AS FAMILIES RETURN",
     "RSF drone strikes widen against the power grid while displaced "
     "families return to war-battered Khartoum, Al Jazeera reports."),
    (7, "UAE JAILS EIGHT FOR LIFE OVER ARMS",
     "A UAE court sentences eight people to life in prison over arms "
     "supplies to Sudan's army, Al Jazeera reports."),
    (8, "COP31 DEADLOCK AS TALKS NEAR END",
     "In Antalya, deadlock persists as countries launch a 'climate reality "
     "check' with time running short at the summit."),
    (9, "HAYABUSA2 DROPS ASTEROID LANDING",
     "Engine trouble forces Japan's JAXA probe to change plans and give up "
     "its asteroid landing, Space.com reports."),
    (10, "VOYAGER 1 A LIGHT-DAY FROM EARTH",
     "NASA confirms the probe has passed one light-day out, 25.9bn km, the "
     "first human-made object to do so. Its signal took a day to arrive."),
    (11, "NICHOLLS 118* AS NZ FIGHT BACK",
     "Day two is under way in Wellington: Nicholls 118 not out, Phillips "
     "103 not out, after their 173-run stand rescued New Zealand from 70 "
     "for 5."),
    (12, "WORLD CHILDREN'S DAY MARKED TODAY",
     "The annual observance falls today, 20 November, with events for "
     "children around the world."),
    (13, "GULF STATES CONDEMN RIYADH ATTACK",
     "Qatar, Kuwait and the Gulf Cooperation Council condemn the missile "
     "attack on Riyadh, reports say."),
]

ALSO = [
    "WASHINGTON - Trump to hold a White House press conference Friday.",
    "NEW YORK - Stocks end a two-day rally; crude oil falls over 3%.",
    "BRASILIA - Lula, re-elected 25 Oct, in no hurry to name his next cabinet.",
    "BRASILIA - Brazil Senate passes a fiscal adjustment bill late Wednesday.",
    "CARACAS - Delcy Rodriguez tours Turkey, Qatar and UAE on trade and energy.",
    "BERLIN - Europe agrees a united line for Ukraine talks at the Berlin summit.",
    "MOSCOW - Putin invites Europeans to Moscow to clarify their Ukraine position.",
    "MADRID - Spain heads to elections on 29 Nov; Sanchez seeks re-election.",
    "RIYADH - Coalition destroys four missiles aimed at the south.",
    "SANAA - Coalition strikes on Sanaa reported by Houthi-run Saba.",
    "KYIV - Drones kill one; Austrian, Dutch embassies and cathedral hit.",
    "DR CONGO - Ebola cases more than double, health officials report.",
    "AFRICA - WHO: AI is helping reinforce polio surveillance across Africa.",
    "DHAKA - Fire at Muhammad Yunus's ancestral home; arson suspected.",
    "NEW DELHI - Modi meets the Prince and Princess of Wales.",
    "NEW DELHI - India signs a Rs 1,976-crore deal for Navy Barak upgrades.",
    "MUMBAI - Sensex gains 1.21%, Nifty 1.14% on strong buying.",
    "VIENNA - IAEA: North Korea is expanding uranium enrichment at Yongbyon.",
    "SHENZHEN - APEC leaders discuss trade, investment and tech cooperation.",
    "NEW DELHI - Modi inaugurates the FICCI centenary convention.",
    "NEW YORK - Nvidia chief Jensen Huang ousted amid espionage scandal.",
    "ASIA - Women's Asian Hockey Champions Trophy begins.",
    "GOA - 57th IFFI adds an animation section with five international films.",
]

DATE_CHECK = [
    "ICJ: Myanmar guilty of Rohingya genocide, 9-6, a court first.",
    "Trump, Xi and Putin meet 81 minutes in Shenzhen.",
    "Anthropic shares begin trading after $83 pricing.",
    "GTA VI goes on sale; first-day sales estimates follow.",
    "Fiji declares a disaster over drought and water shortages.",
    "Top court clears ex-PM Han Duck-soo in martial-law case.",
    "Ukraine hits the Crimean Bridge with Ruta missiles.",
    "Houthi missile damages Riyadh's PIF Tower.",
]

FOOTER = ("Sources: Reuters, AFP, BBC, AP, The Hindu, IMD, Al Jazeera, "
          "Space.com, IAEA. All illustrations are original drawings.")

# ---------------------------------------------------------------- layout
MX = 16                 # left margin; content spans MX .. 1008
CW = 992                # content width
COLW = 320              # lead column width
MIDW = 488              # mid / also / date-check column width


def section_head(x, y, text, scale=1, color=RED):
    draw_text(x, y, text, scale, color)
    return y + 7 * scale + 4


def draw_masthead():
    draw_text_centered(MX + CW // 2, 18, "ONE DAY \u00b7 ONE PAGE \u00b7 THE WHOLE WORLD",
                       1, RED)
    draw_text_centered(MX + CW // 2, 32, "THE FRIDAY GAZETTE", 6, INK)
    hline(MX, 80, CW, INK, 2)
    draw_text(MX, 86, "MORNING EDITION", 1, GREY)
    draw_text_centered(MX + CW // 2, 86, "FRIDAY 20 NOVEMBER 2026", 1, INK)
    draw_text(MX + CW - text_w("36 STORIES \u00b7 ONE PAGE", 1), 86,
              "36 STORIES \u00b7 ONE PAGE", 1, GREY)
    hline(MX, 98, CW, INK, 1)


def draw_chips(y):
    widths = []
    total = 0
    for name, n in CHIPS:
        label = "%s %d" % (name, n)
        w = text_w(label, 1) + 14
        widths.append(w)
        total += w
    total += 8 * (len(CHIPS) - 1)
    x = MX + (CW - total) // 2
    for (name, n), w in zip(CHIPS, widths):
        label = "%s %d" % (name, n)
        fill_rect(x, y, w, 18, PANEL)
        rect_outline(x, y, w, 18, RULE)
        draw_text(x + 7, y + 6, label, 1, INK)
        x += w + 8
    return y + 18


def draw_stats(y):
    bw = 162
    gap = 4
    for i, (num, label) in enumerate(STATS):
        x = MX + i * (bw + gap)
        fill_rect(x, y, bw, 52, PANEL)
        rect_outline(x, y, bw, 52, RULE)
        draw_text_centered(x + bw // 2, y + 5, num, 3, RED)
        lab_lines = wrap_text(label, bw - 12, 1)
        ly = y + 30
        for ln in lab_lines[:2]:
            draw_text_centered(x + bw // 2, ly, ln, 1, INK)
            ly += 9
    return y + 52


def draw_leads(y):
    top = y
    for i, (h1, h2, body, ill) in enumerate(LEADS):
        x = MX + i * (COLW + 16)
        ill(x, top, COLW, 72)
        rect_outline(x, top, COLW, 72, RULE)
        draw_text(x, top + 80, "%d. %s" % (i + 1, h1), 2, INK)
        draw_text(x, top + 96, h2, 2, INK)
        hline(x, top + 114, COLW, RULE)
        n = draw_para(x, top + 120, body, COLW, 1, INK, leading=2)
        print("lead %d body lines: %d (max 6)" % (i + 1, n))
        if i < 2:
            vline(x + COLW + 8, top, 182, RULE)
    return top + 182


def draw_mids(y):
    top = y
    for idx, (num, head, body) in enumerate(MIDS):
        col = 0 if idx < 5 else 1
        row = idx if idx < 5 else idx - 5
        x = MX + col * (MIDW + 16)
        ry = top + row * 46
        ICONS[num](x, ry + 4)
        tx = x + 46
        draw_text(tx, ry, "%d. %s" % (num, head), 2, INK)
        n = draw_para(tx, ry + 17, body, MIDW - 46, 1, INK, leading=2)
        print("mid %d body lines: %d (max 2)" % (num, n))
        if row < 4:
            hline(x, ry + 42, MIDW, (200, 192, 172))
    return top + 5 * 46


def draw_map_section(y):
    top = y
    section_head(MX, top, "WHERE IT HAPPENED", 1, RED)
    map_x, map_y, map_w, map_h = MX, top + 14, 660, 140
    fill_rect(map_x, map_y, map_w, map_h, SEA)
    rect_outline(map_x, map_y, map_w, map_h, INK)
    lon0, lon1 = -170.0, 190.0
    lat0, lat1 = 75.0, -55.0

    def proj(lon, lat):
        px_ = map_x + (lon - lon0) * map_w / (lon1 - lon0)
        py_ = map_y + (lat0 - lat) * map_h / (lat0 - lat1)
        return (px_, py_)

    # faint graticule
    for lon in range(-150, 181, 30):
        gx, _ = proj(lon, 0)
        vline(int(gx), map_y, map_h, (52, 76, 110))
    for lat in range(60, -60, -30):
        _, gy = proj(0, lat)
        hline(map_x, int(gy), map_w, (52, 76, 110))
    for poly in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in poly]
        fill_poly(pts, LAND)
        poly_outline(pts, LAND_EDGE)
    # numbered markers (small cartographic offsets where stories share a city)
    MARKER_NUDGE = {2: (-10, 6), 3: (10, -6), 7: (9, 2), 13: (-9, 2)}
    for num in sorted(MARKERS):
        lon, lat = MARKERS[num]
        mx, my = proj(lon, lat)
        dx, dy = MARKER_NUDGE.get(num, (0, 0))
        mx += dx
        my += dy
        label = str(num)
        bw = text_w(label, 1) + 5
        bx = int(mx - bw // 2)
        by = int(my - 6)
        fill_rect(bx, by, bw, 12, RED)
        rect_outline(bx, by, bw, 12, PAPER)
        draw_text(bx + 3, by + 3, label, 1, PAPER)
    # legend rail
    lx = MX + 660 + 16
    lw = CW - 660 - 16
    draw_text(lx, top, "KEY TO THE MAP", 1, RED)
    ly = top + 16
    for num in sorted(MARKER_PLACE):
        draw_text(lx, ly, "%d. %s" % (num, MARKER_PLACE[num]), 1, INK)
        ly += 10
    return top + 14 + map_h


def draw_also(y):
    top = y
    section_head(MX, top, "ALSO ON FRIDAY 20 NOVEMBER \u2014 23 MORE STORIES",
                 1, RED)
    draw_text(MX, top + 12,
              "From the Friday morning news cycle, including late-Thursday reports.",
              1, GREY)
    ly = top + 26
    for idx, item in enumerate(ALSO):
        num = 14 + idx
        col = 0 if idx < 12 else 1
        row = idx if idx < 12 else idx - 12
        x = MX + col * (MIDW + 16)
        line = "%d. %s" % (num, item)
        w = text_w(line, 1)
        if w > MIDW:
            print("ALSO %d TOO WIDE: %d px > %d: %s" % (num, w, MIDW, line))
        draw_text(x, ly + row * 10, line, 1, INK)
    return ly + 12 * 10


def draw_date_check(y):
    top = y
    fill_rect(MX, top, CW, 66, PANEL)
    rect_outline(MX, top, CW, 66, RED, 2)
    draw_text(MX + 8, top + 5,
              "DATE CHECK \u2014 THESE STORIES BROKE ON THURSDAY 19 NOVEMBER, "
              "NOT ON FRIDAY", 1, RED)
    for idx, item in enumerate(DATE_CHECK):
        col = 0 if idx < 4 else 1
        row = idx if idx < 4 else idx - 4
        x = MX + 8 + col * (MIDW + 8)
        draw_text(x, top + 20 + row * 10, "\u00b7 " + item, 1, INK)
    return top + 66


def draw_footer(y):
    hline(MX, y, CW, RULE)
    draw_text_centered(MX + CW // 2, y + 5, FOOTER, 1, GREY)
    return y + 14


def main():
    fill_rect(0, 0, W, H, PAPER)
    rect_outline(6, 6, W - 12, H - 12, INK, 2)
    rect_outline(10, 10, W - 20, H - 20, RULE, 1)
    draw_masthead()
    y = draw_chips(104)
    y = draw_stats(y + 6)
    y = draw_leads(y + 6)
    y = draw_mids(y + 6)
    y = draw_map_section(y + 6)
    y = draw_also(y + 6)
    y = draw_date_check(y + 6)
    y = draw_footer(y + 6)
    print("final y: %d (page 1024, frame at 1014)" % y)
    paper_grain()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")
    size = save_png(out)
    print("wrote %s (%d bytes)" % (out, size))
    print("stories: 3 leads + 10 mid + 23 also = %d"
          % (len(LEADS) + len(MIDS) + len(ALSO)))
    print("chips total: %d" % sum(n for _, n in CHIPS))


if __name__ == "__main__":
    main()
