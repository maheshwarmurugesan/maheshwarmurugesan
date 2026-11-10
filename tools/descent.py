"""THE DESCENT: pixel-art wastewater journey for the profile README.

Builds one tall world (224 x 1640 logical px) and slices it into 10 looping
panels that stack down the page.

    python3 descent.py OUT          # writes OUT/pN/fNNN.png + OUT/world.png
    for p in 0..9: ffmpeg -framerate 12.5 -i OUT/p$p/f%03d.png \\
        -filter_complex "split[a][b];[a]palettegen=stats_mode=full[q];[b][q]paletteuse=dither=none:diff_mode=rectangle" \\
        -loop 0 descent-$p.gif
"""
import math, os, random, sys
from PIL import Image, ImageDraw

BG = (13, 17, 23); PANEL = (16, 21, 28); AIR = (10, 13, 18)
SKY2 = (18, 24, 32)
SOIL = (26, 21, 16); SOIL2 = (38, 30, 21); SOIL3 = (19, 15, 12)
GREEN = (61, 214, 111); GREEN_D = (42, 122, 63); GREEN_DD = (23, 64, 42)
CONC = (91, 100, 112); CONC_L = (123, 135, 148); CONC_D = (58, 66, 76)
PIPE = (75, 85, 99); PIPE_D = (48, 56, 66)
CREAM = (240, 234, 214); TAN = (201, 163, 107); BROWN = (138, 90, 43); BROWN_D = (74, 48, 24)
GRAY = (107, 114, 128); GRAYD = (64, 72, 84); STEEL = (154, 165, 177); DARK = (43, 51, 61)
YEL = (255, 210, 74); ORANGE = (255, 154, 60); RED = (255, 90, 90)
UV = (169, 112, 255); UV_L = (220, 196, 255); UV_D = (70, 46, 128)
WHITE = (255, 255, 255); BLACK = (8, 10, 14)
SLUDGE = (96, 66, 36); SLUDGE_L = (128, 92, 52); FLOC = (124, 100, 62)
TW = (70, 130, 170)
# water colour leaving each stage: flush, screen, grit, aeration, clarifier, UV, river
C = [(92, 62, 34), (110, 84, 44), (116, 104, 60), (70, 128, 120), (58, 150, 180), (60, 170, 225), (64, 180, 240)]

FONT = {
 'A': "010101111101101", 'B': "110101110101110", 'C': "011100100100011", 'D': "110101101101110",
 'E': "111100110100111", 'F': "111100110100100", 'G': "011100101101011", 'H': "101101111101101",
 'I': "111010010010111", 'J': "001001001101010", 'K': "101101110101101", 'L': "100100100100111",
 'M': "101111111101101", 'N': "110101101101101", 'O': "111101101101111", 'P': "110101110100100",
 'Q': "010101101111011", 'R': "110101110101101", 'S': "011100010001110", 'T': "111010010010010",
 'U': "101101101101111", 'V': "101101101101010", 'W': "101101111111101", 'X': "101101010101101",
 'Y': "101101010010010", 'Z': "111001010100111",
 '0': "111101101101111", '1': "010110010010111", '2': "110001010100111", '3': "110001010001110",
 '4': "101101111001001", '5': "111100110001110", '6': "011100111101111", '7': "111001010010010",
 '8': "111101111101111", '9': "111101111001110",
 '.': "000000000000010", ',': "000000000010100", ':': "000010000010000", '-': "000000111000000",
 '/': "001001010100100", '>': "100010001010100", '<': "001010100010001", '!': "010010010000010",
 '?': "110001010000010", "'": "010010000000000", '+': "000010111010000", '%': "101001010100101",
 '~': "000001001101010", '#': "111111111111111",
}

def clamp(v, a=0.0, b=1.0): return max(a, min(b, v))
def lerp(a, b, f): return tuple(int(round(a[i] + (b[i] - a[i]) * f)) for i in range(3))
def shade(c, f): return tuple(int(clamp(v * f, 0, 255)) for v in c)
def P(v): return int(round(v))
def rect(d, x0, y0, x1, y1, c): d.rectangle([P(x0), P(y0), P(x1), P(y1)], fill=c)
def px(d, x, y, c): d.point((P(x), P(y)), fill=c)

def text(d, x, y, s, c, sc=1):
    x = P(x); y = P(y)
    for ch in s:
        if ch == '~':      # check mark, 5 wide
            for k, j in ((4, 0), (3, 1), (0, 2), (2, 2), (1, 3)):
                d.rectangle([x + k * sc, y + (j + 1) * sc, x + k * sc + sc - 1, y + (j + 1) * sc + sc - 1], fill=c)
            x += 6 * sc; continue
        g = FONT.get(ch)
        if g:
            for j in range(5):
                for k in range(3):
                    if g[j * 3 + k] == '1':
                        d.rectangle([x + k * sc, y + j * sc, x + k * sc + sc - 1, y + j * sc + sc - 1], fill=c)
        x += 4 * sc

def spr(d, x, y, rows, pal, outline=None):
    x = P(x); y = P(y)
    if outline:
        hh, ww = len(rows), len(rows[0])
        for j in range(-1, hh + 1):
            for k in range(-1, ww + 1):
                inside = 0 <= j < hh and 0 <= k < ww and rows[j][k] != '.'
                if inside: continue
                for dj, dk in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = j + dj, k + dk
                    if 0 <= a < hh and 0 <= b < ww and rows[a][b] != '.':
                        d.point((x + k, y + j), fill=outline); break
    for j, row in enumerate(rows):
        for k, ch in enumerate(row):
            if ch in pal: d.point((x + k, y + j), fill=pal[ch])

# ---------------------------------------------------------------- sprites
DROP = ["....B....", "...BBB...", "...BBB...", "..BBBBB..", ".BBHBBBB.", ".BHBBBBB.",
        "BBWKBWKBB", "BBBBBBBBB", ".BBBBBBB.", "..BBBBB.."]
POOP = [".....P.....", "....PPP....", "...PPPPP...", "...PLPPP...", "..PPPPPPP..", "..PWKPWKP..",
        ".PPPPPPPPP.", ".PLPMMMPPP.", "PPPPPPPPPPP", ".PPPPPPPPP."]
DUCK = ["..YY...", ".YKYO..", ".YYY...", "YYYYYY.", "YYYYYY.", ".YYYY.."]
RAG = ["CC.C.", ".CCCC", "CC.CC"]
WIPE = ["WWWW", "WGWW", "WWWW"]
STICK = ["S.....", "SSSSSS"]
GERM = ["R.R.R", ".RRR.", "RKRKR", ".RRR.", "R.R.R"]
GERM2 = [".R.R.", "RRRRR", ".KRK.", "RRRRR", ".R.R."]
MIC_O = [".GGG.", "GGKG.", "GG...", "GGGG.", ".GGG."]
MIC_C = [".GGG.", "GGKGG", "GGGGG", "GGGGG", ".GGG."]
FISH = ["F..FFF.", "FFFFFKF", "FFFFFFF", "F..FFF."]
DRONE = ["....S....", ".GGGGGGG.", ".GKKKKKG.", ".GKKKKKG.", ".GGGGGGG.", "..S...S.."]
SIZES = {'rag': (5, 3), 'duck': (7, 6), 'wipe': (4, 3), 'stick': (6, 2)}
ITEM_SPR = {'rag': (RAG, {'C': (206, 196, 176)}), 'duck': (DUCK, {'Y': YEL, 'K': BLACK, 'O': ORANGE}),
            'wipe': (WIPE, {'W': WHITE, 'G': STEEL}), 'stick': (STICK, {'S': BROWN})}

def flip(rows): return [r[::-1] for r in rows]

def draw_drop(d, x, y, body, mood, shades, t, dizzy=False):
    rows = [list(r) for r in DROP]
    if dizzy:
        rows[6] = list("BBWKBKWBB" if (t // 2) % 2 else "BBKWBWKBB")
    if shades:
        rows[6] = list("KKWKKKKKK"); rows[7] = list("BKKKBKKKB")
    if mood == 'grump':
        rows[8] = list(".BMMMMMB."); rows[9] = list("..BBBBB..")
        if not shades: rows[5] = list(".MMBBMMB.") if False else rows[5]
    elif mood == 'ok':
        rows[8] = list(".BBMMMBB.")
    else:
        if not shades: rows[7] = list("BBMBBBMBB")
        rows[8] = list(".BBMMMBB.")
    rows = ["".join(r) for r in rows]
    pal = {'B': body, 'H': shade(body, 1.5), 'W': WHITE, 'K': BLACK, 'M': shade(body, 0.35)}
    spr(d, x - 4, y - 5, rows, pal, outline=BLACK)


# =====================================================================
# THE DESCENT: one tall pixel world (224 x 1640), sliced into 10 looping
# panels that stack down the README. Every animation is periodic in L
# frames so each panel loops seamlessly.
# =====================================================================
TAU = 2 * math.pi
W, L, SCALE = 224, 64, 4
PHS = [160] * 9 + [200]
OY = [sum(PHS[:i]) for i in range(len(PHS))]
WH = sum(PHS)
K = C
CIN = [K[0], K[0], K[0], K[1], K[2], K[3], K[4], K[4], K[5], K[5]]
COUT = [K[0], K[0], K[1], K[2], K[3], K[4], K[4], K[5], K[5], K[6]]
TANKX = {2: (36, 196), 3: (196, 36), 4: (36, 196), 5: (196, 36), 7: (36, 196), 9: (58, 128)}
BRICK = (96, 54, 46); BRICK_D = (70, 40, 36); MORTAR = (40, 28, 28)
FATC = (208, 198, 150); FATD = (168, 158, 116); BONE = (168, 158, 136)
ROOMC = (13, 17, 23); SKIN = (232, 190, 150); BLUE = (70, 110, 190); DIM = (150, 150, 140)
HOME = (22, 28, 38)

def rect(d, x0, y0, x1, y1, c):
    x0, x1 = sorted((P(x0), P(x1))); y0, y1 = sorted((P(y0), P(y1)))
    d.rectangle([x0, y0, x1, y1], fill=c)
def saw(t, n=1, off=0.0): return ((t * n / L) + off) % 1.0
def wav(t, n=1, off=0.0): return math.sin(TAU * (t * n / L + off))
def tri(t, n=1, off=0.0):
    v = saw(t, n, off); return 1 - abs(2 * v - 1)

class Off:
    """ImageDraw proxy that shifts everything down by oy (panel-local coords)."""
    def __init__(s, d, oy): s.d = d; s.oy = oy
    def rectangle(s, xy, fill=None, outline=None):
        s.d.rectangle([xy[0], xy[1] + s.oy, xy[2], xy[3] + s.oy], fill=fill, outline=outline)
    def point(s, xy, fill=None): s.d.point((xy[0], xy[1] + s.oy), fill=fill)
    def line(s, xy, fill=None):
        s.d.line([v + (s.oy if i % 2 else 0) for i, v in enumerate(xy)], fill=fill)
    def ellipse(s, xy, fill=None, outline=None):
        s.d.ellipse([xy[0], xy[1] + s.oy, xy[2], xy[3] + s.oy], fill=fill, outline=outline)
    def polygon(s, pts, fill=None): s.d.polygon([(x, y + s.oy) for x, y in pts], fill=fill)

def panel_of(y):
    for p in range(len(OY) - 1, -1, -1):
        if y >= OY[p]: return p
    return 0
def wcol(x, y):
    p = panel_of(y); f = 0.0
    if p in TANKX:
        xa, xb = TANKX[p]; f = clamp((x - xa) / (xb - xa))
    return lerp(CIN[p], COUT[p], f)

def dense(pts):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(round(math.hypot(x1 - x0, y1 - y0))))
        for i in range(n): out.append((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n))
    out.append(pts[-1]); return out

# ---------------------------------------------------------------- plumbing
ARC = [(58 + 70 * s / 20, 1520 + 14 * (s / 20) - 150 * (s / 20) * (1 - s / 20)) for s in range(21)]
SEGS = [('pipe', [(160, 106), (160, 128), (200, 128), (200, 210)]),
        ('free', [(200, 210), (200, 226), (44, 226), (40, 236), (40, 292)]),
        ('pipe', [(40, 292), (40, 308), (24, 308), (24, 406), (36, 406)]),
        ('free', [(36, 406), (70, 404), (110, 404), (130, 414), (150, 404), (196, 406)]),
        ('pipe', [(196, 406), (200, 406), (200, 560), (196, 560)]),
        ('free', [(196, 560), (36, 560)]),
        ('pipe', [(36, 560), (24, 560), (24, 720), (36, 720)]),
        ('free', [(36, 720), (60, 728), (90, 716), (120, 730), (150, 718), (180, 726), (196, 722)]),
        ('pipe', [(196, 722), (200, 722), (200, 878), (196, 878)]),
        ('free', [(196, 878), (36, 878)]),
        ('pipe', [(36, 878), (24, 878), (24, 1186), (36, 1186)]),
        ('free', [(36, 1186), (66, 1188), (66, 1236)]),
        ('pipe', [(66, 1236), (108, 1236), (108, 1200), (118, 1200)]),
        ('free', [(118, 1200), (196, 1200)]),
        ('pipe', [(196, 1200), (200, 1200), (200, 1408), (24, 1408), (24, 1520), (58, 1520)]),
        ('free', ARC + [(136, 1543), (236, 1545)])]
PATH = []
for kind_, pts_ in SEGS:
    for q_ in dense(pts_)[:-1]: PATH.append((q_[0], q_[1], kind_))
FLANGES = [(200, 1), (24, 2), (200, 3), (24, 4), (200, 5), (24, 6), (24, 7), (200, 8), (24, 9)]

SLUDGE_LINE = dense([(184, 604), (184, 618), (5, 618), (5, 1030), (54, 1030)])
RAS_LINE = dense([(116, 930), (116, 942), (214, 942), (214, 670), (38, 670), (38, 704)])
WAS_LINE = dense([(116, 942), (5, 942)])
LATERAL = dense([(38, 101), (38, 122), (155, 122)])
GAS_LINE = dense([(78, 1004), (78, 1000), (112, 1000), (112, 1022), (140, 1022)])
FLARE_LINE = dense([(112, 1022), (122, 1022)])
CAKE_LINE = dense([(78, 1084), (78, 1098), (118, 1098), (118, 1077)])
POWER_LINE = dense([(172, 1018), (219, 1018), (219, 958)])

def thin(d, pts, col, wall=PIPE):
    for x, y in pts: rect(d, x - 2, y - 2, x + 2, y + 2, wall)
    for x, y in pts: rect(d, x - 1, y - 1, x + 1, y + 1, col)
def thinflow(d, pts, t, col, gap=16):
    for i, (x, y) in enumerate(pts):
        if (i - t) % gap == 0: rect(d, x - 1, y - 1, x, y, col)

def main_pipe(d):
    for x, y, k in PATH:
        if k == 'pipe': rect(d, x - 4, y - 4, x + 4, y + 4, PIPE)
    for x, y, k in PATH:
        if k == 'pipe': rect(d, x - 3, y - 3, x + 3, y + 3, wcol(x, y))

# ---------------------------------------------------------------- shared art
def tree(d, x, y):
    rect(d, x - 1, y - 8, x, y - 1, BROWN_D)
    for cx, cy, r in ((x - 1, y - 12, 5), (x - 4, y - 10, 3), (x + 3, y - 11, 3)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GREEN_DD)
    for dx, dy in ((-3, -15), (0, -16), (2, -13), (-5, -11), (3, -10), (-1, -12)): px(d, x + dx, y + dy, GREEN_D)

def room(d, x0, y0, x1, y1, seed):
    rect(d, x0, y0, x1, y1, ROOMC); rnd = random.Random(seed)
    for x in range(x0 + 4, x1, 8):
        for y in range(y0 + 4, y1, 8): px(d, x, y, (20, 26, 34))
    for x in range(x0, x1 + 1):
        if rnd.random() < 0.35: px(d, x, y0, SOIL2)
        if rnd.random() < 0.2: px(d, x, y1, SOIL2)
    for y in range(y0, y1 + 1):
        if rnd.random() < 0.35: px(d, x0, y, SOIL2)
        if rnd.random() < 0.35: px(d, x1, y, SOIL2)

def lamp(d, x, y):
    rect(d, x, y - 3, x, y - 1, GRAY); rect(d, x - 1, y, x + 1, y, YEL)
    for dx, dy in ((-2, 1), (2, 1), (-1, 1), (1, 1), (0, 1), (0, 2), (-1, 2), (1, 2)): px(d, x + dx, y + dy, (70, 58, 22))

def title(d, x, tag, name, cap, level):
    text(d, x, 3, tag, TAN); text(d, x, 9, name, CREAM, 2); text(d, x, 21, cap, DIM)
    text(d, 128, 3, "CLEAN", GRAY)
    for s in range(6): rect(d, 150 + s * 5, 3, 153 + s * 5, 7, GREEN if s < level else DARK)

def tankwater(d, p, x0, y0, x1, y1, floorfn=None, nb=8):
    xa, xb = TANKX[p]
    for x in range(x0, x1 + 1):
        f = round(clamp((x - xa) / (xb - xa)) * nb) / nb
        col = lerp(CIN[p], COUT[p], f); yb = int(floorfn(x)) if floorfn else y1
        if yb < y0: continue
        rect(d, x, y0, x, yb, col); rect(d, x, y0 + (yb - y0) * 0.62, x, yb, shade(col, 0.86))
        px(d, x, y0, shade(col, 1.3))
def shimmer(d, x0, x1, y, t, c=WHITE):
    for x in range(x0, x1 + 1):
        if (x * 3 + t) % 16 == 0: px(d, x, y, c)

def person(d, x, y, step=0, hat=YEL, shirt=ORANGE):
    rows = [".HHH.", ".SSS.", ".SSS.", "..B..", "BBBBB", "..B..", "..B..",
            ".L.L." if step % 2 == 0 else "..L..", ".L.L." if step % 2 == 0 else ".L.L."]
    spr(d, x - 2, y - 8, rows, {'H': hat, 'S': SKIN, 'B': shirt, 'L': BLUE})

def drone(d, x, y, t, look=0, spin=True):
    rot = ("RRRR.RRRR" if t % 2 else "..RR.RR..") if spin else "..RRRRR.."
    rows = [list(r) for r in [rot] + DRONE]; rows[3][4 + look] = 'W'
    spr(d, x - 4, y, ["".join(r) for r in rows], {'G': GREEN, 'K': BLACK, 'W': WHITE, 'S': STEEL, 'R': STEEL}, outline=BLACK)
def plate(d, x, y, msg, col=GREEN):
    bw = 4 * len(msg) + 4 + (2 if '~' in msg else 0)
    d.rectangle([x, y, x + bw, y + 8], fill=PANEL, outline=GREEN_D); text(d, x + 3, y + 2, msg, col)
def beam(d, x, y0, y1, t):
    for y in range(y0, y1):
        if (y + t) % 2 == 0: px(d, x + round(math.sin((y + t) * TAU / 8)), y, GREEN_D)

def bricks(d, x0, y0, x1, y1, a=BRICK, b=BRICK_D, m=MORTAR):
    for y in range(y0, y1 + 1):
        row = (y - y0) // 4
        for x in range(x0, x1 + 1):
            if (y - y0) % 4 == 3 or (x + (4 if row % 2 else 0)) % 8 == 7: c = m
            else: c = a if ((x + (4 if row % 2 else 0)) // 8 + row) % 3 else b
            px(d, x, y, c)

RAT = ["P.RRRR.", ".RRRRKR", "..R..R."]; RAT2 = ["P.RRRR.", ".RRRRKR", ".R....R"]
BAT = ["B.....B", "BBBKBBB", ".B.B.B."]; BAT2 = [".......", "BBBKBBB", "B.BBB.B"]
GULL = ["..WW...", ".WKWO..", "WWWWW..", ".WWW...", "..Y...."]
GULL2 = ["W.WW.W.", ".WKWO..", ".WWWW..", ".WWW...", "..Y...."]
CAR = ["...CCCCCC.....", "..CGGCGGGC....", ".CCCCCCCCCCCC.", "CCCCCCCCCCCCCY", ".KK......KK..."]
CAT = ["B.B....", "BBB....", "BGB..B.", "BBBB.B.", "BBBBBB."]
FROG = [".G.G.", "GKGKG", "GGGGG", "G...G"]
CRAB = ["R.....R", "RR.R.RR", ".RRRRR.", "R.R.R.R"]; CRAB2 = ["R.....R", "RR.R.RR", ".RRRRR.", ".R.R.R."]
BEAR = ["..TTTTTT..", ".TTTTTTTT.", "TTKTTTTTTT", "TTTTTTTTT.", ".L.L.L.L.."]
BEAR2 = ["..TTTTTT..", ".TTTTTTTT.", "TTKTTTTTTT", "TTTTTTTTT.", "L.L.L.L..."]

# ---------------------------------------------------------------- level geometry helpers
def sx2(y): return 62 + (100 - y) * 12 / 44
def floor3(x):
    if x <= 170: return 113
    if x < 178: return 113 + (x - 170) * 11 / 8
    if x <= 190: return 124
    return 124 - (x - 190) * 10 / 6
def floor5(x): return 124 - abs(x - 116) * 8 / 80
CHAIN = dense([(46, 110), (168, 110), (172, 106), (172, 76), (168, 72), (46, 72), (42, 76), (42, 106), (46, 110)])[:-1]

# ---------------------------------------------------------------- static levels
def soil_base(d):
    rnd = random.Random(1)
    rect(d, 0, 100, W - 1, WH - 1, SOIL)
    for _ in range(5200): px(d, rnd.randint(0, W - 1), rnd.randint(104, WH - 1), rnd.choice([SOIL2, SOIL3]))
    for _ in range(110):
        x = rnd.randint(0, W - 4); y = rnd.randint(110, WH - 4); w = rnd.randint(2, 5)
        rect(d, x, y, x + w, y + 1 + w // 3, (36, 31, 28)); px(d, x + 1, y, (52, 46, 40))
    for y0 in range(150, WH, 97):
        for x in range(0, W, 3): px(d, x, y0 + round(3 * math.sin(x * 0.08 + y0)), SOIL3)
    for _ in range(26):
        px(d, rnd.randint(0, W - 1), rnd.randint(200, WH - 1), rnd.choice([(90, 200, 220), (220, 120, 220), YEL]))

def p0_static(d):
    rnd = random.Random(11)
    for _ in range(46): px(d, rnd.randint(0, W - 1), rnd.randint(0, 62), DARK)
    d.ellipse([190, 8, 204, 22], fill=CREAM)
    for x, y in ((194, 13), (198, 17), (199, 18), (200, 11)): px(d, x, y, (200, 194, 176))
    for x, w, h in ((0, 16, 34), (60, 22, 44), (84, 18, 28), (204, 20, 40), (100, 16, 50)):
        rect(d, x, 100 - h, x + w, 99, SKY2)
        for _ in range(h // 4): px(d, x + rnd.randint(2, w - 2), 100 - h + rnd.randint(2, h - 3), GREEN_DD)
    rect(d, 0, 100, W - 1, 103, (30, 34, 42))
    for x in range(4, W, 12): rect(d, x, 102, x + 4, 102, (74, 76, 60))
    text(d, 8, 4, "FOLLOW THE FLUSH", CREAM, 2); text(d, 28, 17, "SCROLL DOWN. IT GETS CLEANER.", DIM)
    # little house
    d.polygon([(16, 74), (38, 60), (60, 74)], fill=BROWN_D)
    rect(d, 20, 74, 56, 99, (104, 62, 48)); rect(d, 48, 58, 52, 68, BRICK)
    rect(d, 34, 88, 40, 99, BROWN_D); px(d, 39, 94, YEL)
    rect(d, 23, 79, 31, 87, BROWN_D); rect(d, 24, 80, 30, 86, (200, 170, 80))
    rect(d, 45, 79, 53, 87, BROWN_D)
    tree(d, 92, 100)
    for x in (72, 110):
        rect(d, x, 80, x, 99, GRAY); rect(d, x - 2, 79, x + 2, 79, GRAY); px(d, x, 80, YEL)
        for dx, dy in ((-1, 81), (1, 81), (0, 81), (0, 82)): px(d, x + dx, dy, (70, 58, 22))
    # apartment tower
    rect(d, 116, 26, 204, 27, CONC_L); rect(d, 118, 28, 202, 99, CONC)
    rect(d, 166, 17, 178, 25, BROWN_D); rect(d, 165, 16, 179, 16, BROWN); rect(d, 168, 25, 168, 26, GRAY); rect(d, 176, 25, 176, 26, GRAY)
    rect(d, 192, 10, 192, 25, GRAY)
    for ya, yb in ((30, 51), (54, 75), (78, 98)):
        for xa, xb in ((120, 157), (163, 200)):
            rect(d, xa, ya, xb, yb, HOME)
            for x in range(xa + 3, xb, 6):
                for y in range(ya + 3, yb, 6): px(d, x, y, (30, 38, 50))
            px(d, (xa + xb) // 2, ya, YEL); px(d, (xa + xb) // 2, ya + 1, (110, 92, 36))
        rect(d, 130, yb + 1, 190, yb + 1, PIPE_D)
    rect(d, 159, 28, 161, 104, PIPE); rect(d, 161, 28, 161, 104, PIPE_D)
    # A shower
    rect(d, 121, 33, 127, 33, STEEL); rect(d, 126, 34, 129, 34, STEEL); rect(d, 122, 50, 134, 51, CONC_L)
    for y in range(31, 51, 2): px(d, 137, y, TW)
    person(d, 128, 49, 0, hat=BROWN, shirt=SKIN); rect(d, 149, 37, 152, 43, (150, 60, 60)); px(d, 150, 36, STEEL)
    # B toilet + phone scroller
    rect(d, 194, 38, 198, 46, CREAM); rect(d, 193, 37, 199, 37, WHITE)
    rect(d, 186, 45, 194, 46, WHITE); rect(d, 188, 47, 193, 51, CREAM)
    rect(d, 189, 35, 191, 37, SKIN); rect(d, 189, 34, 191, 34, BROWN_D); rect(d, 189, 38, 191, 44, ORANGE)
    rect(d, 185, 44, 189, 45, BLUE); rect(d, 185, 46, 185, 51, BLUE); rect(d, 186, 40, 188, 40, SKIN)
    rect(d, 168, 40, 170, 42, CREAM); px(d, 169, 39, STEEL)
    # C kitchen
    rect(d, 122, 68, 152, 75, BROWN_D); rect(d, 122, 67, 152, 67, TAN); rect(d, 128, 68, 138, 70, STEEL)
    rect(d, 132, 61, 132, 66, STEEL); rect(d, 132, 61, 135, 61, STEEL); px(d, 135, 62, STEEL)
    rect(d, 142, 65, 147, 66, WHITE); rect(d, 143, 63, 146, 64, WHITE); rect(d, 153, 57, 157, 75, STEEL); px(d, 154, 64, DARK)
    # D laundry
    rect(d, 170, 60, 186, 75, STEEL); rect(d, 170, 60, 186, 62, GRAY); px(d, 172, 61, GREEN); px(d, 174, 61, RED)
    d.ellipse([173, 64, 183, 74], fill=BLACK, outline=GRAY)
    rect(d, 190, 70, 197, 75, TAN); rect(d, 191, 68, 196, 69, (150, 60, 60))
    # E bath
    rect(d, 124, 90, 150, 97, CREAM); rect(d, 126, 91, 148, 93, TW); rect(d, 124, 97, 150, 97, (205, 198, 180))
    rect(d, 130, 86, 132, 89, SKIN); rect(d, 130, 85, 132, 85, BROWN_D); rect(d, 150, 84, 150, 90, STEEL); rect(d, 147, 84, 150, 84, STEEL)
    # F cat + fishbowl
    rect(d, 176, 90, 194, 91, BROWN); rect(d, 178, 92, 178, 98, BROWN_D); rect(d, 192, 92, 192, 98, BROWN_D)
    d.ellipse([180, 81, 190, 90], fill=TW, outline=STEEL); rect(d, 182, 81, 188, 81, HOME)
    # cleanout + manhole shaft
    rect(d, 153, 100, 167, 111, CONC); rect(d, 153, 100, 167, 100, CONC_L); rect(d, 158, 104, 162, 107, CONC_D)
    rect(d, 181, 100, 191, 100, STEEL)
    rect(d, 181, 104, 191, 159, MORTAR); rect(d, 182, 104, 190, 159, (12, 12, 16))
    for y in range(106, 160, 4): rect(d, 184, y, 188, y, GRAYD)
    # underground extras
    for i in range(10): px(d, 92 - i // 2, 104 + i, BROWN_D); px(d, 93 + i // 3, 104 + i, BROWN_D)
    for x in range(0, 150, 4): rect(d, x, 112, x + 1, 112, (110, 96, 40))
    for x, y in ((120, 146), (121, 147), (122, 148), (123, 149), (119, 145), (124, 150), (118, 147), (125, 148)): px(d, x, y, BONE)
    text(d, 132, 140, "SEWER MAIN", (104, 82, 56)); text(d, 174, 146, "V", (104, 82, 56))

def p1_static(d):
    bricks(d, 26, 34, 214, 88)
    bricks(d, 30, 40, 210, 84, (24, 18, 20), (20, 15, 17), (15, 12, 14))
    for x, y in ((30, 40), (31, 40), (30, 41), (210, 40), (209, 40), (210, 41)): px(d, x, y, BRICK_D)
    text(d, 40, 45, "WIPES CLOG PIPES", (120, 90, 164)); text(d, 124, 47, "NO GREASE", (160, 84, 84))
    rect(d, 30, 60, 210, 61, (62, 54, 54)); rect(d, 30, 61, 210, 61, (44, 38, 40))
    rect(d, 30, 66, 210, 84, K[0]); rect(d, 30, 76, 210, 84, shade(K[0], 0.85))
    # manhole shaft down from the street
    rect(d, 181, 0, 191, 39, MORTAR); rect(d, 182, 0, 190, 41, (12, 12, 16))
    for y in range(2, 60, 4): rect(d, 184, y, 188, y, GRAYD)
    # wet well / pump station
    rect(d, 18, 84, 62, 142, CONC); rect(d, 18, 84, 62, 84, CONC_L); rect(d, 22, 88, 58, 138, AIR)
    rect(d, 30, 84, 50, 88, K[0])
    for x in (26, 46):
        rect(d, x, 128, x + 8, 136, STEEL); rect(d, x, 128, x + 8, 128, WHITE); rect(d, x + 2, 131, x + 6, 133, DARK)
        rect(d, x + 4, 122, x + 4, 127, GRAY)
    text(d, 66, 96, "PUMP STATION", TAN)
    text(d, 84, 108, "BOSS: FATBERG", RED)
    rect(d, 84, 115, 134, 118, DARK); rect(d, 85, 116, 118, 117, RED)
    # dino fossil
    for i in range(52):
        x = 118 + i; y = 134 - round(7 * math.sin(i / 52 * math.pi))
        px(d, x, y, BONE)
        if i % 2 == 0: px(d, x, y - 1, BONE)
        if 10 < i < 40 and i % 4 == 0: rect(d, x, y + 1, x, y + 2 + (6 - abs(i - 25) // 3), BONE)
    rect(d, 168, 128, 178, 134, BONE); px(d, 172, 130, SOIL); px(d, 173, 130, SOIL)
    for x in range(170, 179, 2): px(d, x, 135, BONE)
    rect(d, 176, 136, 178, 136, BONE); rect(d, 136, 136, 136, 142, BONE); rect(d, 150, 136, 150, 142, BONE)
    # treasure
    rect(d, 192, 138, 204, 146, BROWN); rect(d, 192, 138, 204, 139, BROWN_D); rect(d, 192, 141, 204, 141, YEL); rect(d, 197, 140, 199, 143, YEL)
    title(d, 8, "B1 // SEW-001", "THE SEWER", "ONLY FLUSH THE 3 P'S: PEE, POO, PAPER.", 0)

def p2_static(d):
    room(d, 14, 30, 210, 104, 2)
    for x in (48, 150): lamp(d, x, 34)
    rect(d, 14, 60, 210, 61, GRAY)
    for x in range(14, 211, 2): px(d, x, 60, STEEL)
    rect(d, 14, 53, 210, 53, GRAYD)
    for x in range(16, 210, 10): rect(d, x, 54, x, 59, GRAYD)
    rect(d, 32, 62, 35, 104, CONC); rect(d, 197, 62, 200, 104, CONC); rect(d, 32, 101, 200, 104, CONC)
    d.polygon([(100, 101), (120, 122), (140, 122), (160, 101)], fill=CONC)
    tankwater(d, 2, 36, 76, 196, 100)
    wc = shade(lerp(CIN[2], COUT[2], 0.5), 0.8)
    d.polygon([(104, 101), (122, 118), (138, 118), (156, 101)], fill=wc)
    rect(d, 36, 101, 103, 101, CONC_L); rect(d, 157, 101, 196, 101, CONC_L)
    rect(d, 172, 93, 190, 100, CONC); rect(d, 172, 93, 190, 93, CONC_L)
    for k in range(7): px(d, 126 + (k * 5) % 9, 117 - k % 2, TAN)
    # screen drive, dumpster
    rect(d, 70, 45, 80, 53, ORANGE); rect(d, 70, 45, 80, 45, YEL); rect(d, 73, 48, 77, 49, BROWN)
    for k in range(8): px(d, 77 + k, 55 - k // 3, STEEL)
    rect(d, 84, 51, 102, 59, GREEN_DD); rect(d, 83, 50, 103, 50, GREEN_D)
    for k, c in enumerate(((206, 196, 176), WHITE, YEL, BROWN)): rect(d, 87 + k * 4, 48, 89 + k * 4, 49, c)
    # grit drive + classifier + bin
    rect(d, 124, 45, 136, 53, TAN); rect(d, 124, 45, 136, 45, CREAM); rect(d, 127, 48, 133, 49, BROWN)
    rect(d, 130, 54, 130, 104, STEEL)
    for i in range(60):
        x = 141 + i * 24 / 60; y = 116 - i
        rect(d, x - 1, y, x + 1, y, STEEL); px(d, x, y, DARK)
    rect(d, 160, 51, 174, 59, (104, 84, 52)); rect(d, 162, 49, 172, 50, TAN); rect(d, 164, 48, 169, 48, TAN)
    # flume sensor
    rect(d, 181, 40, 181, 59, GRAY); rect(d, 179, 62, 183, 64, STEEL)
    d.rectangle([173, 30, 189, 43], fill=BLACK, outline=GRAY); text(d, 174, 32, "FLOW", GREEN_D)
    plate(d, 112, 36, "RAGS OUT ~")
    title(d, 36, "B2 // SCR-101 GRT-201", "HEADWORKS", "TRASH, RAGS AND GRIT GET OFF HERE.", 1)

def p3_static(d):
    room(d, 14, 28, 210, 128, 3)
    for x in (60, 170): lamp(d, x, 32)
    rect(d, 14, 58, 210, 59, GRAY)
    for x in range(14, 211, 2): px(d, x, 58, STEEL)
    rect(d, 14, 52, 210, 52, GRAYD)
    for x in range(16, 210, 10): rect(d, x, 53, x, 57, GRAYD)
    rect(d, 32, 60, 35, 117, CONC); rect(d, 197, 60, 200, 128, CONC)
    for x in range(36, 197):
        fy = int(floor3(x)); rect(d, x, fy + 1, x, fy + 3, CONC)
    tankwater(d, 3, 36, 70, 196, 0, floorfn=floor3)
    for x in range(36, 197):
        fy = int(floor3(x)); rect(d, x, max(fy - 2, 110) if x < 172 else 116, x, fy, SLUDGE)
        if x < 172: px(d, x, fy - 2, SLUDGE_L)
    rect(d, 36, 66, 44, 76, CONC_D); rect(d, 37, 67, 43, 70, (176, 156, 110))
    for i, (x, y) in enumerate(CHAIN):
        if i % 3 == 0: px(d, x, y, GRAYD)
    person(d, 118, 57, 0)
    for i in range(18): px(d, 121 + i // 3, 55 + i, BROWN)
    plate(d, 140, 34, "SCUM OFF ~")
    title(d, 8, "B3 // PRI-201", "PRIMARY", "HEAVY STUFF SINKS. GREASE FLOATS. BOTH LEAVE.", 2)

def p4_static(d):
    room(d, 14, 28, 210, 130, 4)
    for x in (100, 190): lamp(d, x, 38)
    rect(d, 36, 57, 196, 58, GRAY)
    for x in range(36, 197, 2): px(d, x, 57, STEEL)
    rect(d, 32, 58, 35, 130, CONC); rect(d, 197, 58, 200, 130, CONC); rect(d, 32, 127, 200, 130, CONC)
    tankwater(d, 4, 36, 66, 196, 126)
    rect(d, 44, 36, 84, 56, CONC_D); rect(d, 43, 35, 85, 36, CONC)
    for cx in (54, 72): d.ellipse([cx - 6, 40, cx + 6, 52], fill=(24, 30, 38), outline=GRAY)
    rect(d, 84, 50, 90, 50, GRAY); rect(d, 90, 50, 90, 124, GRAY); rect(d, 44, 124, 190, 125, GRAY)
    for x in range(48, 190, 12): rect(d, x, 123, x + 2, 123, STEEL)
    # microscope lens
    d.ellipse([109, 34, 131, 56], fill=shade(lerp(CIN[4], COUT[4], 0.4), 1.25), outline=STEEL)
    for k in range(6): px(d, 131 + k, 54 + k, STEEL); px(d, 132 + k, 54 + k, GRAY)
    for k in range(0, 9, 2): px(d, 118 - k // 2, 58 + k, GRAYD); px(d, 124 + k // 2, 58 + k, GRAYD)
    text(d, 112, 28, "X400", TAN)
    # DO probe + panel
    d.rectangle([158, 46, 168, 56], fill=BLACK, outline=GRAY); text(d, 171, 49, "DO", TAN)
    rect(d, 163, 57, 163, 92, GRAYD); rect(d, 162, 92, 164, 96, STEEL)
    plate(d, 150, 36, "AIR: AUTO ~")
    title(d, 36, "B4 // AER-301", "AERATION", "PUMP IN AIR. BILLIONS OF BUGS DO THE REST.", 3)

def p5_static(d):
    room(d, 14, 28, 210, 134, 5)
    for x in (70, 170): lamp(d, x, 32)
    rect(d, 32, 60, 35, 120, CONC); rect(d, 197, 60, 200, 120, CONC)
    for x in range(32, 201):
        fy = int(floor5(x)) if 36 <= x <= 196 else 116
        rect(d, x, fy + 1, x, fy + 3, CONC); px(d, x, fy + 1, CONC_L)
    rect(d, 109, 125, 123, 132, CONC)
    tankwater(d, 5, 36, 68, 196, 0, floorfn=floor5)
    rect(d, 111, 124, 121, 130, SLUDGE)
    rect(d, 32, 56, 200, 57, STEEL); rect(d, 32, 53, 200, 53, GRAY)
    for x in range(34, 200, 6): px(d, x, 55, STEEL); px(d, x + 3, 54, GRAY)
    rect(d, 109, 45, 123, 53, GREEN_D); rect(d, 109, 45, 123, 45, GREEN); rect(d, 112, 48, 120, 49, GREEN_DD)
    rect(d, 46, 69, 46, 84, CONC_L); rect(d, 36, 84, 46, 84, CONC_L)
    text(d, 34, 147, "< WAS: TO DIGESTER", (120, 96, 64)); text(d, 126, 147, "RAS: BACK TO WORK ^", (120, 96, 64))
    plate(d, 68, 36, "TSS OK ~")
    d.rectangle([216, 150, 223, 158], fill=(28, 34, 42), outline=GRAY); px(d, 220, 152, YEL); px(d, 219, 153, YEL); px(d, 220, 154, YEL); px(d, 219, 155, YEL)
    title(d, 12, "B5 // CLR-401", "SECONDARY", "BUGS SETTLE OUT. CLEAR WATER SPILLS OVER.", 4)

def egg_hw(y): return 24 * math.sqrt(max(0.0, 1 - ((y - 84) / 38) ** 2))
def p6_static(d):
    room(d, 34, 28, 214, 150, 6)
    rect(d, 208, 118, 223, 142, AIR)
    for x in (130, 196): lamp(d, x, 32)
    rect(d, 34, 143, 223, 150, CONC_D); rect(d, 34, 143, 223, 143, CONC)
    # egg digester
    rect(d, 60, 122, 96, 128, CONC); rect(d, 62, 128, 66, 142, CONC); rect(d, 90, 128, 94, 142, CONC)
    d.ellipse([52, 44, 104, 124], fill=CONC_L); d.ellipse([54, 46, 102, 122], fill=(54, 50, 26))
    for y in range(70, 122):
        hw = egg_hw(y); rect(d, 78 - hw, y, 78 + hw, y, (74, 52, 30) if y > 72 else (104, 76, 44))
    for a in range(0, 360, 18):
        px(d, 78 + 25 * math.cos(math.radians(a)), 84 + 39 * math.sin(math.radians(a)), CONC_D)
    rect(d, 78, 50, 78, 108, STEEL)
    d.ellipse([97, 58, 105, 66], fill=CREAM, outline=GRAY); text(d, 106, 69, "95F", DIM)
    text(d, 84, 32, "BIOGAS", (190, 170, 60))
    # flare + CHP
    rect(d, 121, 38, 123, 62, STEEL)
    rect(d, 110, 76, 176, 77, GRAY)
    for k in range(5): px(d, 110 + k, 78 + k, GRAYD); px(d, 176 - k, 78 + k, GRAYD)
    d.rectangle([140, 52, 172, 75], fill=(28, 34, 42), outline=STEEL)
    d.ellipse([143, 57, 157, 71], fill=BLACK, outline=GRAY)
    rect(d, 160, 56, 170, 72, GREEN_DD)
    for x, y in ((166, 58), (165, 59), (164, 60), (163, 61), (164, 62), (165, 62), (166, 62), (165, 63), (164, 64), (163, 65), (162, 66)):
        px(d, x, y, YEL)
    rect(d, 166, 44, 167, 51, STEEL)
    text(d, 176, 46, "POWER ^", YEL)
    # centrifuge + conveyor
    d.rectangle([118, 100, 146, 116], fill=STEEL, outline=GRAY); rect(d, 122, 104, 142, 112, BLACK)
    rect(d, 120, 117, 121, 142, GRAYD); rect(d, 143, 117, 144, 142, GRAYD)
    text(d, 122, 93, "SPIN", DIM)
    rect(d, 146, 120, 180, 121, GRAY)
    for x in range(148, 180, 6): px(d, x, 122, GRAYD)
    # farm poster
    d.rectangle([184, 84, 210, 110], fill=(18, 26, 30), outline=TAN); text(d, 190, 87, "FARM", TAN)
    rect(d, 186, 106, 208, 108, BROWN_D)
    title(d, 40, "B6 // DIG-501", "SOLIDS", "BUGS EAT SLUDGE, BURP GAS. GAS MAKES POWER.", 4)

LAMPS7 = (76, 82, 88, 94)
def p7_static(d):
    room(d, 14, 28, 210, 126, 7)
    for x in (66, 150): lamp(d, x, 32)
    rect(d, 32, 52, 35, 124, CONC); rect(d, 100, 52, 103, 124, CONC); rect(d, 32, 121, 103, 124, CONC)
    tankwater(d, 7, 36, 60, 99, 78)
    rect(d, 36, 79, 99, 90, (28, 28, 34)); rect(d, 36, 91, 99, 104, (150, 124, 84)); rect(d, 36, 105, 99, 112, (70, 74, 82))
    rnd = random.Random(70)
    for _ in range(70): px(d, rnd.randint(36, 99), rnd.randint(79, 90), (54, 54, 66))
    for _ in range(120): px(d, rnd.randint(36, 99), rnd.randint(91, 104), rnd.choice([(172, 146, 102), (128, 104, 68)]))
    for _ in range(26):
        x = rnd.randint(36, 97); y = rnd.randint(105, 111); rect(d, x, y, x + 2, y + 1, (112, 116, 126))
    rect(d, 36, 113, 99, 120, lerp(CIN[7], COUT[7], 0.3))
    text(d, 80, 82, "COAL", (120, 120, 132)); text(d, 80, 95, "SAND", (70, 52, 28)); text(d, 80, 106, "ROCK", (24, 26, 30))
    text(d, 44, 44, "SAND FILTER", TAN)
    rect(d, 114, 58, 117, 100, CONC); rect(d, 197, 58, 200, 100, CONC); rect(d, 114, 97, 200, 100, CONC)
    tankwater(d, 7, 118, 70, 196, 96)
    for x in range(130, 185):
        col = lerp(wcol(x, OY[7]), UV, 0.22); rect(d, x, 71, x, 96, col); rect(d, x, 87, x, 96, shade(col, 0.86))
    rect(d, 130, 62, 130, 96, STEEL); rect(d, 184, 62, 184, 96, STEEL); rect(d, 126, 62, 188, 63, GRAY)
    text(d, 124, 42, "UV REACTOR", TAN); text(d, 124, 51, "SHADES ON", YEL)
    d.rectangle([186, 36, 198, 56], fill=(28, 34, 42), outline=GRAY); rect(d, 188, 39, 196, 44, BLACK)
    title(d, 36, "B7 // FLT-601 DIS-701", "POLISH", "SAND TRAPS THE LAST BITS. UV ZAPS THE GERMS.", 5)

SENS = ((60, "PH"), (90, "DO"), (120, "TSS"), (150, "NH3"))
def p8_static(d):
    room(d, 28, 28, 188, 108, 8)
    rect(d, 28, 106, 188, 108, GRAYD); rect(d, 28, 106, 188, 106, GRAY)
    for x in (70, 130): lamp(d, x, 31)
    d.rectangle([40, 34, 104, 62], fill=(8, 16, 14), outline=GRAY)
    for x in range(42, 103, 3): px(d, x, 42, (150, 60, 60))
    text(d, 44, 36, "LIMIT", (150, 60, 60))
    d.rectangle([110, 34, 150, 62], fill=(10, 14, 20), outline=GRAY); text(d, 114, 37, "DMR", GREEN)
    rect(d, 112, 66, 116, 70, GREEN); text(d, 119, 66, "EFFLUENT", CREAM)
    rect(d, 44, 92, 124, 93, BROWN); rect(d, 46, 94, 47, 105, BROWN_D); rect(d, 121, 94, 122, 105, BROWN_D)
    for x in (50, 68, 86):
        d.rectangle([x, 79, x + 14, 89], fill=BLACK, outline=GRAY); rect(d, x + 6, 90, x + 8, 91, GRAY)
    rect(d, 113, 88, 114, 105, GRAYD); rect(d, 104, 98, 113, 99, GRAYD)
    rect(d, 105, 84, 107, 86, SKIN); rect(d, 105, 83, 107, 83, BROWN_D); px(d, 108, 85, DARK)
    rect(d, 105, 87, 107, 96, GREEN_D); rect(d, 100, 97, 105, 98, BLUE); rect(d, 100, 99, 100, 105, BLUE)
    rect(d, 118, 89, 120, 91, WHITE); px(d, 121, 90, WHITE)
    d.rectangle([158, 50, 178, 105], fill=(20, 24, 30), outline=GRAYD); text(d, 164, 53, "AI", GREEN)
    d.ellipse([172, 32, 182, 42], fill=CREAM, outline=GRAY)
    rect(d, 136, 104, 146, 105, GREEN_D)
    rect(d, 32, 100, 36, 105, BROWN); rect(d, 33, 94, 33, 99, GREEN_D); rect(d, 35, 96, 35, 99, GREEN_D); px(d, 32, 95, GREEN); px(d, 36, 97, GREEN); px(d, 34, 93, GREEN)
    rect(d, 60, 103, 158, 103, GRAYD)
    for x, name in SENS:
        rect(d, x, 103, x, 123, GRAYD); rect(d, x - 2, 119, x + 2, 123, STEEL); text(d, x + 5, 113, name, TAN)
    for x in range(50, 161):
        px(d, x, 124, STEEL); px(d, x, 132, STEEL); px(d, x, 125, shade(K[5], 1.35))
    rect(d, 48, 122, 50, 134, CONC_L); rect(d, 160, 122, 162, 134, CONC_L)
    title(d, 8, "B8 // OPS-801", "MISSION CONTROL", "EVERY DROP MEASURED. THE REPORT FILES ITSELF.", 5)

def cliff_x(y): return 58 + round(2 * math.sin(y * 0.3) + math.sin(y * 0.77))
def over_y(x): return (28 if x < 128 else (28 - (x - 128) * 16 / 10 if x < 138 else 12)) + round(1.5 * math.sin(x * 0.5) + math.sin(x * 1.3))
def p9_static(d):
    for y0, c in ((0, BG), (30, (15, 22, 32)), (44, (20, 32, 44)), (56, (30, 44, 56)), (66, (52, 56, 64)), (74, (86, 68, 62)), (82, (128, 88, 60)), (88, (170, 112, 62))):
        rect(d, 56, y0, W - 1, 93, c)
    rnd = random.Random(9)
    for _ in range(14): px(d, rnd.randint(140, 222), rnd.randint(14, 40), DARK)
    for yy in range(78, 94):
        hw = int(math.sqrt(max(0, 256 - (94 - yy) ** 2)))
        rect(d, 178 - hw, yy, 178 + hw, yy, ORANGE)
        if hw > 3: rect(d, 178 - hw + 3, yy, 178 + hw - 3, yy, YEL)
    d.polygon([(56, 93), (84, 62), (104, 82), (126, 56), (152, 93)], fill=(24, 34, 48))
    for cx, cy in ((84, 62), (126, 56)):
        for k in range(5): rect(d, cx - k, cy + k, cx + k, cy + k, CREAM if k < 3 else (150, 160, 170))
    for x in range(56, W):
        hgt = 3 + int(2 * math.sin(x * 0.09) + 1.5 * math.sin(x * 0.31 + 1))
        if 160 < x < 198: hgt = min(hgt, 1)
        rect(d, x, 93 - hgt, x, 93, (16, 44, 36))
        if x % 6 == 0: rect(d, x, 91 - hgt, x, 93 - hgt, GREEN_DD); px(d, x, 90 - hgt, GREEN_D)
    for x in range(56, W):
        rect(d, x, 94, x, 110, K[6]); rect(d, x, 111, x, 130, shade(K[6], 0.88)); rect(d, x, 131, x, 150, shade(K[6], 0.76))
        px(d, x, 94, shade(K[6], 1.3))
    rect(d, 56, 150, W - 1, 165, (40, 58, 60))
    for _ in range(60): px(d, rnd.randint(60, 222), rnd.randint(151, 164), rnd.choice([(60, 80, 82), (30, 44, 48)]))
    for x, w in ((84, 7), (128, 5), (190, 9)): rect(d, x, 148, x + w, 151, (58, 76, 82)); rect(d, x + 1, 147, x + w - 1, 147, (74, 94, 100))
    for y in range(0, 166):
        e = cliff_x(y); rect(d, 0, y, e, y, SOIL); px(d, e, y, (58, 48, 38))
        if y % 5 == 0: px(d, e - 2, y, SOIL2)
    for x in range(56, W):
        oyv = over_y(x); rect(d, x, 0, x, oyv, SOIL); px(d, x, oyv, (58, 48, 38))
        if x % 9 == 0: rect(d, x, oyv + 1, x, oyv + 3 + x % 4, GREEN_DD)
    rect(d, 52, 70, 62, 91, CONC); rect(d, 52, 70, 62, 70, CONC_L)
    rect(d, 147, 93, 153, 93, GREEN_D); px(d, 150, 92, GREEN_D); rect(d, 163, 93, 169, 93, GREEN_D); px(d, 166, 92, GREEN_D)
    for x, hh in ((214, 8), (217, 11), (220, 7), (222, 10)): rect(d, x, 93 - hh, x, 94, GREEN_D); px(d, x, 93 - hh, GREEN)
    rect(d, 205, 83, 205, 96, (60, 60, 64)); rect(d, 208, 83, 208, 96, (60, 60, 64))
    d.ellipse([200, 76, 212, 83], fill=(170, 180, 196)); rect(d, 207, 78, 212, 80, (120, 130, 150))
    text(d, 100, 36, "LEVEL CLEAR!", GREEN, 2); text(d, 112, 49, "THE CYCLE CONTINUES.", CREAM)
    plate(d, 138, 62, "DMR FILED ~")
    rect(d, 0, 166, W - 1, 199, PANEL); rect(d, 0, 166, W - 1, 166, GREEN_DD)
    rect(d, 8, 172, 17, 181, GREEN); text(d, 22, 172, "EFFLUENT", CREAM, 2)
    text(d, 8, 188, "THE WASTEWATER INTELLIGENCE COMPANY", DIM)
    title(d, 36, "B9 // OUT-901", "OUTFALL", "CLEAN WATER GOES HOME.", 6)

def build_static():
    w = Image.new('RGB', (W, WH), BG); d = ImageDraw.Draw(w)
    soil_base(d)
    for p, fn in enumerate((p0_static, p1_static, p2_static, p3_static, p4_static, p5_static, p6_static, p7_static, p8_static, p9_static)):
        fn(Off(d, OY[p]))
    thin(d, LATERAL, K[0])
    main_pipe(d)
    thin(d, SLUDGE_LINE, SLUDGE); thin(d, WAS_LINE, SLUDGE); thin(d, RAS_LINE, (96, 84, 48)); thin(d, CAKE_LINE, (60, 42, 26))
    for line in (GAS_LINE, FLARE_LINE):
        for x, y in line: rect(d, x - 1, y - 1, x + 1, y + 1, (96, 86, 34))
        for x, y in line: px(d, x, y, (190, 170, 60))
    for x, y in POWER_LINE: px(d, x, y, (120, 104, 40))
    o = Off(d, OY[8])
    for x in range(50, 161): px(o, x, 124, STEEL); px(o, x, 132, STEEL); px(o, x, 125, shade(K[5], 1.35))
    rect(o, 48, 122, 50, 134, CONC_L); rect(o, 160, 122, 162, 134, CONC_L)
    return w

# ---------------------------------------------------------------- dynamic levels
def p0_dyn(d, t):
    for k, (x, y) in enumerate(((30, 8), (150, 6), (86, 40), (214, 30), (60, 50), (176, 4))):
        if (t // 8 + k) % 4 == 0: px(d, x, y, CREAM)
    for k in range(3): text(d, 8 + k * 6, 17 + ((t // 8 + k) % 2), "V", GREEN)
    px(d, 192, 9, RED if (t // 8) % 2 else DARK)
    rect(d, 46, 80, 52, 86, ((90, 140, 220), (200, 170, 80), (120, 200, 160), (220, 120, 120))[(t // 4) % 4])
    for k in range(3):
        p = saw(t, 1, k / 3); c = GRAY if p < 0.5 else DARK
        x = 50 + round(2 * wav(t, 2, k / 3)); y = 56 - p * 20
        rect(d, x, y, x + 1 + int(p * 2), y + 1, c)
    for k in range(6): px(d, 126 + k % 4, 35 + saw(t, 4, k / 6) * 13, (150, 200, 240))
    for k in range(3): px(d, 140 + k * 3, 34 + ((t // 8 + k) % 3), (60, 70, 84))
    px(d, 186, 41, WHITE if (t // 16) % 2 else (120, 200, 255))
    rect(d, 135, 63, 135, 67, (150, 200, 240) if t % 2 else (110, 170, 220))
    a = TAU * saw(t, 2)
    px(d, 178 + 3 * math.cos(a), 69 + 3 * math.sin(a), RED); px(d, 178 - 3 * math.cos(a), 69 - 3 * math.sin(a), YEL)
    px(d, 178 + 2 * math.sin(a), 69 + 2 * math.cos(a), (120, 200, 255))
    spr(d, 138, 86 + (t // 16) % 2, ["YY..", "YKO.", "YYY."], {'Y': YEL, 'K': BLACK, 'O': ORANGE})
    for k in range(3):
        if (t // 8 + k) % 3: px(d, 134 + k * 4, 89 - (t // 8 + k) % 2, WHITE)
    spr(d, 166, 94, CAT, {'B': (84, 84, 100), 'G': GREEN if t % 32 > 2 else (84, 84, 100)})
    px(d, 172 + (t // 8) % 2, 93, (84, 84, 100))
    px(d, 185 + round(2 * wav(t, 2)), 86, ORANGE); px(d, 184 + round(2 * wav(t, 2)), 86, ORANGE)
    for i in range(8): px(d, 20 + i, 140 + round(wav(t, 2, i / 8)), (200, 120, 130))
    x = -16 + (W + 32) * saw(t)
    spr(d, x, 95, CAR, {'C': RED, 'G': (150, 200, 240), 'K': BLACK, 'Y': YEL})
    px(d, x + 15, 98, (110, 92, 36))

def p1_dyn(d, t):
    for y in range(54, 67):
        for x in range(197, 204):
            if (y - t * 2 + x) % 4 < 2: px(d, x, y, shade(K[0], 1.3))
    for k in (-1, 1): px(d, 200 + k * (5 + (t // 2) % 3), 65 - (t // 2) % 2, shade(K[0], 1.5))
    shimmer(d, 30, 210, 66, t, shade(K[0], 1.6))
    for x0, off in ((70, 0.0), (120, 0.3), (160, 0.6)): px(d, x0, 41 + saw(t, 2, off) * 24, (120, 140, 150))
    spr(d, 90, 40, BAT if (t // 4) % 2 else BAT2, {'B': (60, 50, 70), 'K': RED})
    spr(d, 142, 40, BAT2, {'B': (60, 50, 70), 'K': RED})
    for off in (0.0, 0.5):
        right = saw(t, 1, off) < 0.5
        rows = RAT if (t // 2) % 2 else RAT2
        spr(d, 40 + 150 * tri(t, 1, off), 57, rows if right else flip(rows), {'R': GRAY, 'P': (220, 140, 150), 'K': BLACK})
    ax = 150 + round(3 * wav(t))
    rect(d, ax, 64, ax + 16, 65, GREEN_D); rect(d, ax + 1, 62, ax + 2, 63, GREEN_D); rect(d, ax + 5, 62, ax + 6, 63, GREEN_D)
    if not 20 <= t < 24: px(d, ax + 1, 62, YEL); px(d, ax + 5, 62, YEL)
    px(d, ax + 15, 64, BLACK)
    fx = 70 + 10 * wav(t); right = math.cos(TAU * t / L) > 0
    spr(d, fx, 74 + round(2 * wav(t, 2)), FISH if right else flip(FISH), {'F': ORANGE, 'K': BLACK})
    s = saw(t); on = s < 0.5
    lvl = 100 + 40 * s if on else 120 - 40 * (s - 0.5)
    rect(d, 22, lvl, 58, 127, K[0]); rect(d, 22, 128, 25, 138, K[0]); rect(d, 35, 128, 45, 138, K[0]); rect(d, 55, 128, 58, 138, K[0])
    rect(d, 26, 137, 54, 138, K[0]); rect(d, 22, lvl, 58, lvl, shade(K[0], 1.3))
    for x in (30, 52): rect(d, x, 89, x, lvl - 3, GRAYD); rect(d, x - 1, lvl - 2, x + 1, lvl, RED)
    for x in (26, 46):
        if on: px(d, x + 3 + (t % 2) * 2, 132, GREEN); px(d, x + 5 - (t % 2) * 2, 132, GREEN)
    text(d, 66, 102, "ON" if on else "OFF", GREEN if on else GRAY)
    if (t // 8) % 2: rect(d, 119, 116, 133, 117, DARK)
    if (t // 4) % 4 == 0: px(d, 198, 136, WHITE); px(d, 202, 139, YEL)
    mx = 84
    rect(d, mx, 144, mx + 9, 149, (74, 62, 60)); rect(d, mx + 1, 143, mx + 8, 143, (74, 62, 60)); rect(d, mx + 2, 141, mx + 7, 142, YEL)
    px(d, mx + 9, 146, (230, 150, 160)); px(d, mx + 7, 145, BLACK)
    sw = (t // 4) % 2
    rect(d, mx + 10, 147 - sw * 3, mx + 13, 147 - sw * 3, BROWN); rect(d, mx + 13, 146 - sw * 3, mx + 14, 148 - sw * 3, STEEL)
    if sw: px(d, mx + 16, 142, SOIL2); px(d, mx + 17, 145, SOIL2)

ITEMS2 = [('rag', 84, 0), ('duck', 71, 10), ('wipe', 92, 22), ('stick', 96, 34), ('rag', 80, 44), ('wipe', 88, 54)]
def rake2(t):
    ph = t % 16
    return 99 - ph * 43 / 11 if ph < 12 else None
def p2_dyn(d, t):
    shimmer(d, 36, 196, 76, t, shade(lerp(CIN[2], COUT[2], 0.5), 1.6))
    for kind, y, s in ITEMS2:
        w, h = SIZES[kind]; rows, pal = ITEM_SPR[kind]; ym = y + h / 2
        xs = sx2(ym) - w - 1; a = math.ceil((xs - 38) / 2.0)
        phr = round((99 - ym) * 11 / 43); b = a + ((phr - s - a) % 16); rd = 11 - phr
        tau = (t - s) % L
        if tau < a: pos = (38 + (xs - 38) * tau / a, y + (tau % 2 if kind != 'duck' else 0))
        elif tau < b:
            pos = (xs, y)
            if kind == 'duck' and (t // 2) % 2: text(d, xs + 2, y - 7, "!", YEL)
        elif tau < b + rd:
            ry = 99 - (phr + tau - b) * 43 / 11; pos = (sx2(ry) - w - 1, ry - h)
            if kind == 'duck': text(d, pos[0] - 26, pos[1] - 2, "QUACK!", YEL)
        elif tau < b + rd + 5:
            q = (tau - b - rd) / 5; pos = (70 + 22 * q, 50 - 30 * q * (1 - q))
        else: continue
        spr(d, pos[0], pos[1], rows, pal)
    for k in range(20):
        p = saw(t, 1, k / 20); r = (8 + (k * 7) % 14) * (1 - p) + 1
        px(d, 130 + r * math.cos(k * 1.7 + TAU * 2 * t / L), 80 + p * 36, TAN if k % 2 else (232, 204, 156))
    wv = int(abs(math.cos(TAU * 2 * t / L)) * 10)
    rect(d, 130 - wv, 103, 130 + wv, 104, TAN)
    for k in range(6):
        p = saw(t, 4, k / 6); px(d, 141 + p * 24, 116 - p * 60, TAN)
    for k in range(2):
        p = saw(t, 4, k / 2); rect(d, 180 - p * 3, 66 + p * 9, 182 + p * 3, 66 + p * 9, GREEN_D)
    rect(d, 176, 39, 176 + round(7 + 4 * wav(t, 2)), 40, GREEN)
    right = saw(t) < 0.5
    person(d, 20 + 34 * tri(t), 59, t // 4)
    dy = 40 + round(wav(t, 2) * 1.5)
    drone(d, 104, dy, t, look=1 if right else -1); beam(d, 104, dy + 8, 76, t)

def p2_front(d, t):
    for y in range(56, 101):
        x = P(sx2(y)); px(d, x, y, STEEL if y % 2 == 0 else CONC_D); px(d, x + 1, y, CONC_D if y % 2 == 0 else GRAY)
    ry = rake2(t)
    if ry is not None:
        x = P(sx2(ry)); rect(d, x - 3, ry, x - 1, ry, TAN); px(d, x - 3, ry - 1, TAN)

def p3_dyn(d, t):
    shimmer(d, 45, 196, 70, t, shade(lerp(CIN[3], COUT[3], 0.5), 1.6))
    n = len(CHAIN)
    for k in range(12):
        i = int(((k + 4 * t / L) / 12) * n) % n; x, y = CHAIN[i]
        if y >= 108: rect(d, x, y - 3, x, y, TAN)
        elif y <= 74: rect(d, x, y - 1, x, y + 2, TAN)
        else: rect(d, x - 2, y, x + 1, y, TAN)
    for cx, cy in ((44, 74), (170, 74), (170, 108), (44, 108)):
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], outline=GRAY)
        a = TAU * saw(t, 4); px(d, cx + 2 * math.cos(a), cy + 2 * math.sin(a), WHITE); px(d, cx, cy, STEEL)
    for k in range(12): px(d, 176 - saw(t, 1, k / 12) * 128, 69, (196, 176, 124))
    for k in range(30):
        x = 48 + (k * 37) % 146; y = 76 + saw(t, 1, ((k * 13) % 64) / 64) * 33
        if y < floor3(x) - 3: px(d, x, y, FLOC)
    spr(d, 70, 47, GULL2 if t < 12 and (t // 2) % 2 else GULL, {'W': WHITE, 'K': BLACK, 'O': ORANGE, 'Y': ORANGE})
    spr(d, 160, 47 + (1 if 30 <= t < 38 else 0), flip(GULL), {'W': WHITE, 'K': BLACK, 'O': ORANGE, 'Y': ORANGE})
    dy = 34 + round(wav(t, 2) * 1.5); drone(d, 132, dy, t); beam(d, 132, dy + 8, 51, t)

MIC4 = [(60, 84, 16, 10, 1, 2, 0.0), (96, 100, 24, 12, 1, 3, 1.0), (130, 86, 22, 10, 2, 1, 2.1), (164, 104, 20, 10, 1, 2, 3.3),
        (112, 114, 40, 5, 1, 2, 4.0), (150, 76, 30, 5, 2, 3, 5.2), (76, 108, 14, 8, 2, 1, 0.7)]
def mic4(k, t):
    bx, by, A, B, k1, k2, ph = MIC4[k]; a = TAU * k1 * t / L + ph
    return bx + A * math.sin(a), by + B * math.sin(TAU * k2 * t / L + ph * 2), math.cos(a) > 0
_r4 = random.Random(4)
DOTS4 = [(_r4.randint(44, 190), _r4.randint(72, 120)) for _ in range(54)]
VIS4 = [[not any(math.hypot(mic4(k, (t - j) % L)[0] - x, mic4(k, (t - j) % L)[1] - y) < 6 for j in range(24) for k in range(len(MIC4)))
         for t in range(L)] for (x, y) in DOTS4]
def p4_dyn(d, t):
    shimmer(d, 36, 196, 66, t, shade(lerp(CIN[4], COUT[4], 0.5), 1.6))
    for j, dx in enumerate(range(48, 190, 12)):
        for k in range(3):
            yy = 122 - saw(t, 2, (j * 5 + k * 21) / 64) * 54
            xx = dx + 1 + round(wav(t, 4, (j + k) / 5))
            px(d, xx, yy, (214, 240, 255))
            if yy < 90: px(d, xx + 1, yy, WHITE)
    nom = None
    for i, (x, y) in enumerate(DOTS4):
        if VIS4[i][t]: px(d, x, y, (158, 104, 50)); px(d, x + 1, y, (120, 78, 38))
        elif VIS4[i][(t - 1) % L] or VIS4[i][(t - 2) % L]: nom = (x, y)
    for x0, y0, horiz, off in ((40, 92, 1, 0.0), (40, 108, 1, 0.4), (70, 122, 0, 0.2), (150, 122, 0, 0.7)):
        for j in range(7):
            sway = round(wav(t, 2, off) * j / 3)
            px(d, x0 + j if horiz else x0 + sway, y0 + sway if horiz else y0 - j, (150, 170, 120))
        hx, hy = (x0 + 7, y0 + round(wav(t, 2, off) * 2)) if horiz else (x0 + round(wav(t, 2, off) * 2), y0 - 8)
        rect(d, hx - 1, hy - 1, hx + 1, hy + 1, (206, 226, 160)); px(d, hx, hy, GREEN_D)
    rx = 176 + 4 * wav(t); ry = 92 + 3 * wav(t, 2, 0.3)
    rect(d, rx, ry, rx + 6, ry + 3, (210, 180, 224)); rect(d, rx + 7, ry + 1, rx + 9, ry + 2, (170, 140, 190))
    px(d, rx, ry - 1 + (t // 2) % 2 * 5, WHITE); px(d, rx + 1, ry + 1, BLACK)
    for k in range(len(MIC4)):
        x, y, right = mic4(k, t)
        rows = MIC_O if (t + k) % 4 < 2 else MIC_C
        spr(d, x - 2, y - 2, rows if right else flip(rows), {'G': GREEN, 'K': BLACK}, outline=GREEN_DD)
    if nom: text(d, nom[0] - 5, nom[1] - 8, "NOM", GREEN)
    bx = 104 + 30 * wav(t); right = math.cos(TAU * t / L) > 0
    rows = BEAR if (t // 4) % 2 else BEAR2
    spr(d, bx, 118, rows if not right else flip(rows), {'T': (206, 184, 160), 'K': BLACK, 'L': (160, 140, 120)})
    text(d, bx - 14, 111, "WATER BEAR", TAN)
    for cx in (54, 72):
        a = TAU * saw(t, 4)
        for q in range(4):
            aa = a + q * TAU / 4
            d.line([cx, 46, cx + round(4 * math.cos(aa)), 46 + round(4 * math.sin(aa))], fill=STEEL)
        px(d, cx, 46, GREEN)
    big = ["..GGGG..", ".GGGGGG.", "GGGKKGG.", "GGGKKG..", "GGGGG...", "GGGGGG..", ".GGGGGG.", "..GGGG.."] if (t // 4) % 2 else \
          ["..GGGG..", ".GGGGGG.", "GGGKKGGG", "GGGKKGGG", "GGGGGGGG", "GGGGGGGG", ".GGGGGG.", "..GGGG.."]
    spr(d, 113, 41, big, {'G': GREEN, 'K': BLACK}, outline=GREEN_DD)
    if (t // 4) % 2: rect(d, 124, 44, 126, 46, (158, 104, 50))
    lv = round(3 + 2 * wav(t, 2)); rect(d, 160, 54 - lv, 166, 54, GREEN); px(d, 163, 97, GREEN if (t // 4) % 2 else DARK)
    for k in range(3): px(d, 36 + k * 2, 64 + ((t + k) % 2), (150, 140, 90))
    dy = 37 + round(wav(t, 2) * 1.5); drone(d, 141, dy, t)

def p5_dyn(d, t):
    shimmer(d, 47, 196, 68, t, WHITE)
    for k in range(34):
        x = 60 + (k * 53) % 132; y = 72 + saw(t, 1, ((k * 11) % 64) / 64) * 36
        if y < floor5(x) - 6: px(d, x, y, FLOC); px(d, x + k % 2, y, FLOC)
    for x in range(36, 197):
        fy = int(floor5(x)); th = 5 + (1 if (x + t // 4) % 8 < 3 else 0)
        rect(d, x, fy - th, x, fy, SLUDGE); px(d, x, fy - th, SLUDGE_L)
    rect(d, 115, 50, 117, 124, STEEL); rect(d, 117, 50, 117, 124, GRAY)
    rect(d, 104, 68, 104, 80, CONC_L); rect(d, 128, 68, 128, 80, CONC_L)
    Lr = int(abs(math.cos(TAU * t / L)) * 72)
    for sgn in (-1, 1):
        for dx in range(2, Lr + 1):
            x = 116 + sgn * dx; fy = int(floor5(x)); px(d, x, fy - 3, TAN)
            if dx % 8 == 0: rect(d, x, fy - 2, x, fy - 1, CREAM)
    rect(d, 37, 70, 45, 83, shade(K[4], 1.15))
    px(d, 46, 68, WHITE if t % 2 else shade(K[4], 1.5)); px(d, 45, 69, WHITE if t % 2 == 0 else shade(K[4], 1.5))
    px(d, 116, 47, GREEN if (t // 4) % 2 else GREEN_DD)
    a = TAU * saw(t, 4); d.ellipse([156, 138, 164, 146], fill=STEEL, outline=GRAY)
    px(d, 160 + 2 * math.cos(a), 142 + 2 * math.sin(a), GREEN); px(d, 160, 142, BLACK)
    dy = 38 + round(wav(t, 2) * 1.5); drone(d, 60, dy, t); beam(d, 60, dy + 8, 52, t)

def p6_dyn(d, t):
    for k in range(12):
        x = 60 + (k * 17) % 36; y = 120 - saw(t, 2, k / 12) * 49
        if abs(x - 78) < egg_hw(y) - 2: px(d, x, y, (140, 110, 70)); px(d, x + (k % 2), y - 1, (110, 84, 50))
    for k in range(6):
        x = 62 + (k * 13) % 32; y = 69 - saw(t, 2, k / 6) * 18
        if abs(x - 78) < egg_hw(y) - 2: px(d, x, y, (190, 170, 60))
    wv = int(abs(math.cos(TAU * 2 * t / L)) * 8); rect(d, 78 - wv, 106, 78 + wv, 107, TAN)
    a = TAU * saw(t); px(d, 101 + 2 * math.cos(a), 62 + 2 * math.sin(a), RED); px(d, 101, 62, BLACK)
    f = t % 4
    for dy_, wd, c in ((0, 2, RED), (2, 3, ORANGE), (4, 2, YEL)):
        rect(d, 122 - wd + (f % 2), 30 + dy_ + (f == 3), 122 + wd - (f == 1), 31 + dy_, c)
    px(d, 122 + (f - 1), 28 - f % 2, ORANGE); px(d, 122, 36, WHITE)
    a = TAU * saw(t, 4)
    for q in range(3):
        aa = a + q * TAU / 3
        d.line([150, 64, 150 + round(5 * math.cos(aa)), 64 + round(5 * math.sin(aa))], fill=STEEL)
    px(d, 150, 64, YEL)
    for k in range(3):
        p = saw(t, 2, k / 3); rect(d, 166 + round(2 * wav(t, 2, k / 3)), 42 - p * 12, 167 + round(2 * wav(t, 2, k / 3)) + int(p * 2), 43 - p * 12, GRAYD)
    if (t // 4) % 2: px(d, 165, 60, WHITE)
    for x in range(122, 143):
        if (x + t * 2) % 6 < 2: rect(d, x, 104, x, 112, GRAY)
    for k in range(4):
        x = 146 + saw(t, 2, k / 4) * 34; rect(d, x, 118, x + 2, 119, (60, 42, 26))
    tx = 180 if t < 40 else (180 + (t - 39) * 5 if t < 52 else 240 - (t - 51) * 5)
    fill = t / 40 if t < 40 else (1.0 if t < 52 else 0.0)
    rect(d, tx, 128, tx + 20, 137, (60, 66, 76)); rect(d, tx + 1, 128, tx + 19, 136, BLACK)
    if fill > 0: rect(d, tx + 1, 136 - fill * 7, tx + 19, 136, (70, 50, 30)); rect(d, tx + 4, 135 - fill * 8, tx + 15, 135 - fill * 7, (90, 66, 40))
    rect(d, tx + 21, 124, tx + 31, 137, GREEN); rect(d, tx + 25, 126, tx + 30, 130, (160, 220, 255)); rect(d, tx + 21, 137, tx + 31, 137, GREEN_D)
    for wx in (tx + 4, tx + 15, tx + 26):
        d.ellipse([wx - 2, 137, wx + 2, 141], fill=BLACK, outline=GRAYD)
    if t < 40 and t % 4 < 2: rect(d, 181, 122 + t % 4 * 2, 183, 123 + t % 4 * 2, (60, 42, 26))
    st = int(saw(t) * 4) + 1
    rect(d, 197, 106 - st * 3, 197, 105, GREEN_D)
    if st > 1: px(d, 196, 106 - st * 3 + 1, GREEN); px(d, 198, 106 - st * 3 + 2, GREEN)
    if st > 2: rect(d, 195, 106 - st * 3 - 1, 199, 106 - st * 3, GREEN)
    if st > 3: rect(d, 196, 92, 198, 94, YEL); px(d, 197, 93, ORANGE)
    for k in (190, 204): rect(d, k, 104 - min(st, 2), k, 105, GREEN_DD)

GERMS7 = [(k / 6, 74 + (k * 7) % 20, 136 + (k * 11) % 40) for k in range(6)]
def p7_dyn(d, t):
    shimmer(d, 36, 99, 60, t, WHITE); shimmer(d, 118, 196, 70, t, WHITE)
    for k in range(26):
        x = 38 + (k * 29) % 60; p = saw(t, 1, ((k * 11) % 64) / 64); y = 62 + p * 30
        if y < 79: px(d, x, y, (140, 96, 50))
        elif p < 0.92: px(d, x, 79 + k % 7, (120, 80, 40))
    for k, y in enumerate(LAMPS7):
        for x in range(132, 183, 2):
            off = (t + k) % 2
            px(d, x + off, y - 1, UV_D); px(d, x + 1 - off, y + 1, UV_D)
        rect(d, 132, y, 182, y, UV)
        for x in range(132, 183):
            if (x + t * 2 + k * 3) % 8 < 2: px(d, x, y, UV_L)
    for k, c in enumerate((GREEN, YEL, GREEN)): px(d, 189 + k * 3, 48, c if (t // 4 + k) % 2 else DARK)
    px(d, 189 + (t // 4) % 7, 41 + (t // 8) % 3, GREEN)
    for off, y, zx in GERMS7:
        tau = saw(t, 1, off); x = 120 + tau * 96
        fz = (tau - (zx - 120) / 96) * L
        if x < zx: spr(d, x - 2, y - 2 + (t % 2), GERM if t % 4 < 2 else GERM2, {'R': RED, 'K': BLACK})
        elif fz < 2:
            ly = min(LAMPS7, key=lambda v: abs(v - y))
            d.line([zx + 5, ly, zx + 2, (ly + y) // 2, zx + 4, (ly + y) // 2, zx, y], fill=WHITE)
            spr(d, zx - 2, y - 2, GERM, {'R': WHITE, 'K': UV}); text(d, zx - 6, y - 9, "ZAP", UV_L)
        elif fz < 6:
            spr(d, zx - 2 + fz, y - 2 + fz, GERM2, {'R': GRAY if fz < 4 else DARK, 'K': BLACK})

def p8_dyn(d, t):
    for x in range(42, 103):
        u = (x - 42) / 60
        v = 52 + 3 * math.sin(TAU * (u * 2 + t / L)) + 2 * math.sin(TAU * (u * 5 + 2 * t / L))
        px(d, x, v, GREEN); px(d, x, v + 1, GREEN_DD)
    n = int(saw(t) * 6)
    for i in range(min(n, 4)): rect(d, 114, 45 + i * 4, 114 + (28, 20, 30, 16)[i], 46 + i * 4, GRAY)
    if n >= 4:
        d.rectangle([113, 47, 147, 57], fill=(10, 14, 20), outline=GREEN); text(d, 116, 50, "FILED ~", GREEN)
    for k, x in enumerate((50, 68, 86)):
        for j in range(5):
            hgt = 1 + (j * 3 + k * 2 + t // 4) % 6; rect(d, x + 2 + j * 2, 88 - hgt, x + 2 + j * 2, 88, (GREEN, (120, 200, 255), YEL)[k])
    rect(d, 99 + (t // 2) % 2, 91, 104, 91, SKIN)
    for k in range(2): px(d, 119 + round(wav(t, 2, k / 2)), 87 - saw(t, 2, k / 2) * 6, GRAY)
    for r_ in range(8):
        for c_ in range(4):
            on = ((r_ * 7 + c_ * 13 + t // 4) * 2654435761) % 5 < 2
            px(d, 162 + c_ * 4, 62 + r_ * 5, (GREEN if (r_ + c_) % 3 else YEL) if on else DARK)
    spr(d, 162, 45, CAT, {'B': (104, 104, 120), 'G': (104, 104, 120)})
    px(d, 170, 43 - (t // 16) % 3, DIM)
    a = TAU * saw(t) - TAU / 4; d.line([177, 37, 177 + round(3 * math.cos(a)), 37 + round(3 * math.sin(a))], fill=BLACK)
    drone(d, 141, 97, t, spin=False)
    if (t // 8) % 2: px(d, 148, 100, YEL); px(d, 149, 101, YEL); px(d, 148, 102, YEL)
    for k, (x, name) in enumerate(SENS):
        px(d, x, 121, GREEN if (t // 4 + k) % 2 else DARK)
        for j in range(2):
            p = saw(t, 2, k / 4 + j / 2); dist = p * (20 + 158 - x)
            if dist < 20: px(d, x, 123 - dist, GREEN)
            else: px(d, x + dist - 20, 103, GREEN)

def p9_dyn(d, t):
    for off, y, w in ((0.0, 56, 22), (0.5, 70, 16)):
        cx = 60 + saw(t, 1, off) * 190 - 20
        for dy_, a, b in ((0, 4, w - 6), (2, 0, w), (4, 2, w - 3)):
            x0 = max(cx + a, cliff_x(y + dy_) + 1); x1 = min(cx + b, W - 1)
            if x1 > x0: rect(d, x0, y + dy_, x1, y + dy_ + 1, (150, 146, 160) if dy_ else (196, 180, 184))
        if off == 0.5:
            for k in range(5):
                rx = cx + 3 + k * 3; ry = 77 + saw(t, 4, k / 5) * 12
                if cliff_x(int(ry)) < rx < W: px(d, rx, ry, (120, 170, 220))
    for k in range(6):
        p = saw(t, 1, k / 6)
        if p < 0.8: px(d, 92 + k * 22 + round(2 * wav(t, 2, k / 6)), 92 - p * 26, (150, 190, 210) if p < 0.5 else (90, 110, 130))
    shimmer(d, 62, W - 1, 94, t, WHITE)
    for k in range(0, 8, 2):
        wv = 9 - k; off = ((t // 4) + k) % 3 - 1
        rect(d, 178 - wv + off, 95 + k, 178 + wv + off, 95 + k, YEL if k < 4 else ORANGE)
    for i in range(16):
        x = 62 + i * 0.75; y = 78 + i * i * 0.062
        for j in range(5 - i // 5): px(d, x, y + j, shade(K[5], 1.35) if (i + j - t) % 4 < 2 else K[5])
    for k in range(4): px(d, 70 + ((t + k * 5) % 8), 93 - ((t + k * 3) % 4), WHITE)
    for bx, n in ((96, 7), (140, 6), (176, 8), (210, 6)):
        for j in range(n): px(d, bx + round(wav(t, 2, bx / 50 + j / 12) * 1.6 * j / n), 149 - j, GREEN_D)
    for off, y, c, rightward in ((0.0, 112, ORANGE, True), (0.4, 126, CREAM, True), (0.7, 138, (255, 190, 120), False), (0.2, 120, (255, 120, 140), False)):
        s = saw(t, 1, off); x = 62 + (s if rightward else 1 - s) * 170
        if x < 214: spr(d, x, y, FISH if rightward else flip(FISH), {'F': c, 'K': BLACK})
    s = saw(t, 1, 0.3)
    if s < 0.25:
        q = s / 0.25; spr(d, 186 + 18 * q, 92 - 44 * q * (1 - q), FISH, {'F': GREEN, 'K': BLACK})
        if q < 0.2 or q > 0.85:
            for k in (-2, 0, 2): px(d, (188 if q < 0.5 else 206) + k, 92, WHITE)
    if t < 24: fx, fy = 148, 89
    elif t < 32: q = (t - 24) / 8; fx, fy = 148 + 16 * q, 89 - 28 * q * (1 - q)
    elif t < 56: fx, fy = 164, 89
    else: q = (t - 56) / 8; fx, fy = 164 - 16 * q, 89 - 28 * q * (1 - q)
    spr(d, fx, fy, FROG, {'G': GREEN, 'K': BLACK})
    strike = 40 <= t < 48
    hx, hy = (193, 84) if strike else (197, 65)
    d.line([202, 78, 200 if strike else 201, 80 if strike else 70, hx + 3, hy + 2], fill=(170, 180, 196))
    rect(d, hx, hy, hx + 4, hy + 2, (170, 180, 196)); px(d, hx + 2, hy, BLACK); px(d, hx + 4, hy - 1, (60, 60, 64))
    d.line([hx - 1, hy + 1, hx - 6, hy + 2 + (3 if strike else 0)], fill=YEL)
    kx = 108 + 96 * tri(t); right = saw(t) < 0.5
    rect(d, kx, 92, kx + 15, 93, ORANGE); px(d, kx - 1, 92, ORANGE); px(d, kx + 16, 92, ORANGE)
    rect(d, kx + 7, 86, kx + 9, 91, RED); rect(d, kx + 7, 83, kx + 9, 85, SKIN); rect(d, kx + 7, 82, kx + 9, 82, YEL)
    if (t // 4) % 2: d.line([kx + 3, 84, kx + 13, 93], fill=CREAM)
    else: d.line([kx + 13, 84, kx + 3, 93], fill=CREAM)
    cxr = 100 + 44 * tri(t)
    spr(d, cxr, 146, CRAB if (t // 4) % 2 else CRAB2, {'R': RED})
    for x in (72, 110, 156, 198):
        if (x + t // 8) % 3 == 0: px(d, x, 3 + over_y(x) + 5 + (t // 8) % 2, GREEN_D)
    if (t // 8) % 2 == 0: text(d, 134, 176, "FLUSH TO PLAY AGAIN ^", GREEN)
    dy = 62 + round(wav(t, 2) * 1.5); drone(d, 130, dy, t)

def p1_front(d, t):
    wob = round(wav(t, 2))
    d.polygon([(96, 60 + wob), (104, 55 + wob), (118, 54 + wob), (128, 59 + wob), (131, 68 + wob), (126, 76 + wob), (112, 78 + wob), (100, 76 + wob), (94, 69 + wob)], fill=FATC)
    for x, y in ((100, 62), (122, 70), (110, 74), (116, 58), (104, 70)): rect(d, x, y + wob, x + 2, y + 1 + wob, FATD)
    rect(d, 97, 66 + wob, 100, 67 + wob, WHITE); rect(d, 123, 62 + wob, 126, 63 + wob, WHITE)
    for ex in (106, 116):
        rect(d, ex, 62 + wob, ex + 3, 65 + wob, BLACK); px(d, ex + 1 + (t // 16) % 2, 64 + wob, RED)
    d.line([104, 60 + wob, 109, 62 + wob], fill=BLACK); d.line([121, 60 + wob, 116, 62 + wob], fill=BLACK)
    for k in range(5): px(d, 107 + k * 2, 69 + wob + k % 2, BLACK)

DYN = (p0_dyn, p1_dyn, p2_dyn, p3_dyn, p4_dyn, p5_dyn, p6_dyn, p7_dyn, p8_dyn, p9_dyn)
UV_IDX = next(i for i, (x, y, k) in enumerate(PATH) if panel_of(y) == 7 and k == 'free' and x > 128 and y < OY[7] + 100)

def draw_hero(d, t):
    for j in range(-1, len(PATH) // 128 + 1):
        i = j * 128 + t * 2
        if not 0 <= i < len(PATH): continue
        x, y, kind = PATH[i]; p = panel_of(y)
        if x > W + 6: continue
        body = shade(wcol(x, y), 1.5 if p < 4 else 1.35)
        bob = round(wav(t, 4, j / 3)) if kind == 'free' else 0
        mood = 'grump' if p <= 3 else ('ok' if p <= 6 else 'happy')
        if p == 9 and kind == 'free' and y - OY[9] < 92:
            for k in range(4):
                a = TAU * saw(t, 2, k / 4)
                px(d, x + 9 * math.cos(a), y + 8 * math.sin(a), YEL if (t // 2 + k) % 2 else WHITE)
        for k in (1, 2):
            if (t + k) % 4 < 2:
                bi = max(0, i - 4 - k * 4); px(d, PATH[bi][0], PATH[bi][1] - 1, shade(body, 1.25))
        draw_drop(d, x, y + bob, body, mood, i >= UV_IDX, t)

def draw_front(d, t):
    p1_front(Off(d, OY[1]), t); p2_front(Off(d, OY[2]), t)
    for x, p in FLANGES:
        y = OY[p]
        rect(d, x - 6, y - 5, x + 6, y + 4, PIPE); rect(d, x - 6, y - 5, x + 6, y - 5, CONC_L); rect(d, x - 6, y + 4, x + 6, y + 4, PIPE_D)
        for bx in (x - 5, x + 5): px(d, bx, y - 3, CONC_L); px(d, bx, y + 2, CONC_L)
    rect(d, 153, 100, 167, 111, CONC); rect(d, 153, 100, 167, 100, CONC_L); rect(d, 158, 104, 162, 107, CONC_D)

def draw_flow(d, t):
    for i in range(0, len(PATH)):
        if (i - t * 2) % 16 == 0:
            x, y, k = PATH[i]; g = (i // 16) % 8
            px(d, x + (g * 5) % 5 - 2, y + (g * 3) % 5 - 2, shade(wcol(x, y), 1.35))
    thinflow(d, LATERAL, t, shade(K[0], 1.4)); thinflow(d, SLUDGE_LINE, t, SLUDGE_L); thinflow(d, WAS_LINE, t, SLUDGE_L)
    thinflow(d, RAS_LINE, t, GREEN, 8); thinflow(d, CAKE_LINE, t, SLUDGE_L)
    for line in (GAS_LINE, FLARE_LINE):
        for i, (x, y) in enumerate(line):
            if (i - t) % 8 == 0: px(d, x, y, WHITE)
    for i, (x, y) in enumerate(POWER_LINE):
        if (i - t * 2) % 16 == 0:
            for dx, dy in ((0, -2), (-1, -1), (0, 0), (1, 0), (0, 1), (-1, 2)): px(d, x + dx, y + dy, YEL)

STATIC = build_static()
def render(t):
    w = STATIC.copy(); d = ImageDraw.Draw(w)
    for p, fn in enumerate(DYN): fn(Off(d, OY[p]), t)
    draw_flow(d, t); draw_hero(d, t); draw_front(d, t)
    return w

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "dframes"
    for p in range(len(PHS)): os.makedirs(os.path.join(out, f"p{p}"), exist_ok=True)
    for t in range(L):
        w = render(t)
        if t == 0: w.resize((W * 2, WH * 2), Image.NEAREST).save(os.path.join(out, "world.png"))
        for p in range(len(PHS)):
            im = w.crop((0, OY[p], W, OY[p] + PHS[p]))
            im.resize((W * SCALE, PHS[p] * SCALE), Image.NEAREST).save(os.path.join(out, f"p{p}", f"f{t:03d}.png"))
    print("ok", L, "frames x", len(PHS), "panels")
