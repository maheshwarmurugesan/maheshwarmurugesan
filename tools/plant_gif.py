"""Pixel-art wastewater treatment walkthrough -> frames/ (PNG, 4x) for the profile README.

One flush, followed room by room through the treatment train, Zelda-style
screen scrolls between rooms. Everything is drawn procedurally at 224x100
and upscaled nearest-neighbour.
"""
import math, os, random, sys
from PIL import Image, ImageDraw

RW, SH, NR = 224, 77, 7          # room width, scene height, room count
FW, FH, TOP, SCALE = 224, 100, 11, 4
GY = 40                          # ground line (scene coords)
H = [44, 46, 46, 50, 46, 46, 72] # hold frames per room
PAN = 12

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

TITLES = [("IN-001", "THE FLUSH"), ("SCR-101", "SCREENING"), ("GRT-201", "GRIT"), ("AER-301", "AERATION"),
          ("CLR-401", "SECONDARY"), ("DIS-501", "DISINFECTION"), ("OUT-601", "OUTFALL")]
CAPTIONS = ["EVERY FLUSH STARTS A JOURNEY.",
            "BAR SCREEN: NO WIPES. NO DUCKS. NO EXCEPTIONS.",
            "GRIT CHAMBER: WATER SPINS, SAND SINKS.",
            "AERATION: BILLIONS OF BUGS EAT THE BAD STUFF.",
            "CLARIFIER: SLUDGE SINKS, CLEAR WATER RISES.",
            "UV DISINFECTION: GERMS, MEET PHOTONS.",
            "CLEAN WATER GOES HOME. THE REPORT FILES ITSELF."]
READOUT = ["", "RAGS OUT ~", "GRIT OUT ~", "O2 OK ~", "TSS OK ~", "UV OK ~", "DMR FILED ~"]

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

# ---------------------------------------------------------------- static world
def tree(d, x, y):
    rect(d, x - 1, y - 8, x, y - 1, BROWN_D)
    for cx, cy, r in ((x - 1, y - 12, 5), (x - 4, y - 10, 3), (x + 3, y - 11, 3)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GREEN_DD)
    for dx, dy in ((-3, -15), (0, -16), (2, -13), (-5, -11), (3, -10), (-1, -12)):
        px(d, x + dx, y + dy, GREEN_D)

def base_room(d, r):
    ox = r * RW; rnd = random.Random(100 + r)
    for _ in range(14): px(d, ox + rnd.randint(0, RW - 1), rnd.randint(0, 22), DARK)
    for _ in range(5):
        w = rnd.randint(14, 34); h = rnd.randint(6, 17); x = ox + rnd.randint(0, RW - w)
        rect(d, x, GY - h, x + w, GY - 1, SKY2)
        for _ in range(rnd.randint(0, 3)): px(d, x + rnd.randint(2, w - 2), GY - h + rnd.randint(2, h - 2), GREEN_DD)
    rect(d, ox, GY, ox + RW - 1, SH - 1, SOIL)
    rect(d, ox, GY, ox + RW - 1, GY, GREEN_DD)
    for _ in range(70): px(d, ox + rnd.randint(0, RW - 1), rnd.randint(GY + 2, SH - 1), rnd.choice([SOIL2, SOIL3]))

def pipes(d, ox, x0, x1):
    rect(d, ox + x0, 56, ox + x1, 56, PIPE); rect(d, ox + x0, 64, ox + x1, 64, PIPE_D)
    rect(d, ox + x0, 57, ox + x1, 63, AIR)
    for x in range(x0 + 6, x1, 14):
        rect(d, ox + x, 55, ox + x + 1, 55, PIPE); rect(d, ox + x, 65, ox + x + 1, 65, PIPE_D)

def tank(d, ox, floor=True):
    rect(d, ox + 42, 40, ox + 182, 71, AIR)
    for x0 in (38, 183):
        rect(d, ox + x0, 34, ox + x0 + 3, 71, CONC)
        rect(d, ox + x0, 34, ox + x0 + 3, 34, CONC_L)
        rect(d, ox + x0 + 3, 35, ox + x0 + 3, 71, CONC_D)
    if floor:
        rect(d, ox + 38, 69, ox + 186, 71, CONC); rect(d, ox + 42, 69, ox + 182, 69, CONC_L)
    pipes(d, ox, 0, 37); pipes(d, ox, 187, 223)

def bridge(d, ox, motor_col):
    rect(d, ox + 38, 33, ox + 186, 33, STEEL)
    for x in range(40, 186, 6): px(d, ox + x, 32, STEEL); px(d, ox + x + 3, 31, GRAY)
    rect(d, ox + 38, 30, ox + 186, 30, GRAY)
    rect(d, ox + 106, 23, ox + 118, 30, motor_col); rect(d, ox + 106, 23, ox + 118, 23, shade(motor_col, 1.3))
    rect(d, ox + 106, 30, ox + 118, 30, shade(motor_col, 0.6))
    rect(d, ox + 109, 26, ox + 115, 27, shade(motor_col, 0.6))

def sx(y): return 128 - (y - 30) * 10 / 38     # bar screen x at depth y
def floor4(x): return 72 - abs(x - 112) * 6 / 70

def build_static():
    w = Image.new('RGB', (RW * NR, SH), BG); d = ImageDraw.Draw(w)
    for r in range(NR): base_room(d, r)

    # ---- room 0: house + toilet
    ox = 0
    tree(d, ox + 70, GY)
    rect(d, ox + 94, 7, ox + 182, 9, BROWN); rect(d, ox + 94, 9, ox + 182, 9, BROWN_D)
    rect(d, ox + 96, 10, ox + 180, 39, CONC)
    rect(d, ox + 98, 10, ox + 178, 39, (22, 28, 38))
    for x in range(100, 178, 6):
        for y in range(13, 38, 6): px(d, ox + x, y, (32, 40, 52))
    rect(d, ox + 96, 24, ox + 97, 39, (22, 28, 38))                     # doorway
    rect(d, ox + 110, 14, ox + 122, 23, CONC_L); rect(d, ox + 111, 15, ox + 121, 22, (26, 40, 58))
    rect(d, ox + 116, 15, ox + 116, 22, CONC_L); px(d, ox + 119, 17, CREAM); px(d, ox + 113, 20, DARK)
    px(d, ox + 138, 10, GRAY); px(d, ox + 138, 11, GRAY); rect(d, ox + 137, 12, ox + 139, 13, YEL)
    rect(d, ox + 149, 23, ox + 151, 25, CREAM); px(d, ox + 150, 22, STEEL); px(d, ox + 150, 26, CREAM)
    rect(d, ox + 144, 39, ox + 154, 39, (120, 50, 50))
    rect(d, ox + 170, 18, ox + 176, 31, CREAM); rect(d, ox + 169, 17, ox + 177, 18, WHITE)
    rect(d, ox + 176, 19, ox + 176, 31, (205, 198, 180))
    rect(d, ox + 155, 28, ox + 170, 29, WHITE)
    rect(d, ox + 157, 30, ox + 169, 33, CREAM); rect(d, ox + 160, 34, ox + 168, 36, CREAM)
    rect(d, ox + 159, 37, ox + 169, 39, CREAM)
    rect(d, ox + 157, 33, ox + 169, 33, (205, 198, 180)); rect(d, ox + 159, 39, ox + 169, 39, (205, 198, 180))
    rect(d, ox + 161, 40, ox + 161, 64, PIPE); rect(d, ox + 167, 40, ox + 167, 56, PIPE)
    rect(d, ox + 162, 40, ox + 166, 63, AIR)
    pipes(d, ox, 168, 223); rect(d, ox + 161, 64, ox + 223, 64, PIPE_D)

    # ---- room 1: bar screen
    ox = RW; tank(d, ox)
    rect(d, ox + 20, 18, ox + 20, 39, GRAY); rect(d, ox + 18, 17, ox + 22, 17, GRAY); px(d, ox + 20, 18, YEL)
    for x in range(126, 183, 2): px(d, ox + x, 38, STEEL)
    rect(d, ox + 126, 39, ox + 182, 39, GRAY)
    rect(d, ox + 142, 29, ox + 160, 36, GREEN_DD); rect(d, ox + 141, 29, ox + 161, 29, GREEN_D)
    px(d, ox + 145, 37, DARK); px(d, ox + 157, 37, DARK)
    rect(d, ox + 124, 21, ox + 133, 28, ORANGE); rect(d, ox + 124, 21, ox + 133, 21, YEL)
    rect(d, ox + 124, 28, ox + 133, 28, BROWN); rect(d, ox + 127, 24, ox + 130, 25, BROWN)
    for k in range(9): px(d, ox + 133 + k, 29 + k // 4, STEEL)

    # ---- room 2: grit vortex
    ox = 2 * RW; tank(d, ox, floor=False)
    rect(d, ox + 42, 69, ox + 182, 76, SOIL)
    rect(d, ox + 38, 69, ox + 92, 70, CONC); rect(d, ox + 132, 69, ox + 186, 70, CONC)
    for k in range(7):
        rect(d, ox + 92 + k * 16 / 6, 69 + k, ox + 93 + k * 16 / 6 + 1, 69 + k, CONC)
        rect(d, ox + 131 - k * 16 / 6 - 1, 69 + k, ox + 132 - k * 16 / 6, 69 + k, CONC)
    rect(d, ox + 107, 76, ox + 117, 76, CONC)
    bridge(d, ox, TAN)

    # ---- room 3: aeration
    ox = 3 * RW; tank(d, ox)
    rect(d, ox + 6, 24, ox + 32, 39, CONC_D); rect(d, ox + 5, 23, ox + 33, 24, CONC)
    rect(d, ox + 13, 26, ox + 25, 38, (30, 36, 44)); rect(d, ox + 27, 34, ox + 30, 39, DARK)
    rect(d, ox + 32, 36, ox + 44, 36, GRAY); rect(d, ox + 44, 36, ox + 44, 42, GRAY)

    # ---- room 4: secondary clarifier
    ox = 4 * RW; tank(d, ox, floor=False)
    rect(d, ox + 42, 66, ox + 182, 76, SOIL)
    for x in range(38, 187):
        fy = int(floor4(x)) if 42 <= x <= 182 else 66
        rect(d, ox + x, fy, ox + x, fy + 1, CONC); px(d, ox + x, fy, CONC_L)
    text(d, ox + 52, 71, "< RAS", (104, 82, 56))
    bridge(d, ox, GREEN_D)

    # ---- room 5: UV
    ox = 5 * RW; tank(d, ox)
    for x in range(80, 156, 2): px(d, ox + x, 38, STEEL)
    rect(d, ox + 80, 39, ox + 155, 39, GRAY)
    rect(d, ox + 158, 22, ox + 174, 39, CONC_D); rect(d, ox + 158, 22, ox + 174, 22, CONC)
    rect(d, ox + 161, 25, ox + 171, 30, BLACK)
    rect(d, ox + 62, 28, ox + 62, 39, GRAY)
    for k in range(5): rect(d, ox + 62 - k, 23 + k, ox + 62 + k, 23 + k, YEL)
    px(d, ox + 62, 25, BLACK); px(d, ox + 62, 26, BLACK)

    # ---- room 6: outfall + river
    ox = 6 * RW
    rect(d, ox + 66, 0, ox + 223, SH - 1, BG)
    rnd = random.Random(7)
    for _ in range(12): px(d, ox + rnd.randint(70, 222), rnd.randint(0, 26), DARK)
    rect(d, ox + 66, 30, ox + 223, 37, (15, 22, 31)); rect(d, ox + 66, 38, ox + 223, 43, (19, 30, 40))
    rect(d, ox + 66, 44, ox + 223, 49, (26, 42, 50))
    for yy in range(41, 50):
        hw = int(math.sqrt(max(0, 81 - (50 - yy) ** 2)))
        rect(d, ox + 186 - hw, yy, ox + 186 + hw, yy, ORANGE)
        if hw > 2: rect(d, ox + 186 - hw + 2, yy, ox + 186 + hw - 2, yy, YEL)
    for x in range(66, 224):
        hgt = 2 + int(1.6 * math.sin(x * 0.11) + 1.2 * math.sin(x * 0.37 + 1))
        if 174 < x < 198: hgt = min(hgt, 1)
        rect(d, ox + x, 49 - hgt, ox + x, 49, (14, 32, 28))
        if x % 5 == 0: px(d, ox + x, 49 - hgt, GREEN_DD)
    tree(d, ox + 30, GY)
    pipes(d, ox, 0, 59)
    rect(d, ox + 60, 42, ox + 65, 72, CONC); rect(d, ox + 60, 42, ox + 65, 42, CONC_L)
    rect(d, ox + 65, 43, ox + 65, 72, CONC_D)
    for x, hh in ((56, 6), (58, 9), (61, 7), (63, 10), (65, 6)):
        rect(d, ox + x, 41 - hh, ox + x, 41, GREEN_D); px(d, ox + x, 41 - hh, GREEN)

    for r, (tag, name) in enumerate(TITLES):
        text(d, r * RW + 8, 3, tag, TAN); text(d, r * RW + 8, 10, name, CREAM, 2)
    return w

# ---------------------------------------------------------------- water
def watercol(r, xl):
    if r == 0: return C[0]
    if r == 6: return C[5] if xl < 66 else C[6]
    return lerp(C[r - 1], C[r], clamp((xl - 42) / 140))

def water(d, r, t, lf):
    ox = r * RW
    if r == 0:
        rect(d, ox + 162, 57, ox + 223, 63, C[0])
        if 24 <= lf <= 36: rect(d, ox + 162, 40, ox + 166, 56, C[0])
        for k in range(5): px(d, ox + 164 + (t * 3 + k * 13) % 58, 58 + k % 5, shade(C[0], 1.3))
        return
    if r == 6:
        rect(d, ox, 57, ox + 65, 63, C[5])
        for k in range(5): px(d, ox + (t * 3 + k * 13) % 64, 58 + k % 5, shade(C[5], 1.25))
        rect(d, ox + 66, 50, ox + 223, 76, C[6]); rect(d, ox + 66, 60, ox + 223, 68, shade(C[6], 0.88))
        rect(d, ox + 66, 69, ox + 223, 76, shade(C[6], 0.74))
        for x in range(66, 224):
            px(d, ox + x, 50, shade(C[6], 1.3) if (x + t // 2) % 7 < 4 else WHITE)
        for k in range(0, 6, 2):
            wv = 6 - k; off = ((t // 2) + k) % 3 - 1
            rect(d, ox + 186 - wv + off, 51 + k, ox + 186 + wv + off, 51 + k, YEL if k < 2 else ORANGE)
        return
    cin, cout = C[r - 1], C[r]
    rect(d, ox, 57, ox + 41, 63, cin); rect(d, ox + 183, 57, ox + 223, 63, cout)
    for k in range(4):
        px(d, ox + (t * 3 + k * 11) % 40, 58 + (k * 2) % 5, shade(cin, 1.3))
        px(d, ox + 184 + (t * 3 + k * 11) % 40, 58 + (k * 2) % 5, shade(cout, 1.25))
    nb = 6
    for b in range(nb):
        xa = 42 + 141 * b // nb; xb = 42 + 141 * (b + 1) // nb - 1
        col = lerp(cin, cout, b / (nb - 1))
        if r == 5 and 84 <= xa <= 150: col = lerp(col, UV, 0.22)
        if r == 2:
            rect(d, ox + xa, 43, ox + xb, 68, col); rect(d, ox + xa, 60, ox + xb, 68, shade(col, 0.86))
        elif r == 4:
            for x in range(xa, xb + 1):
                fy = int(floor4(x)); rect(d, ox + x, 43, ox + x, fy - 1, col)
        else:
            rect(d, ox + xa, 43, ox + xb, 68, col); rect(d, ox + xa, 61, ox + xb, 68, shade(col, 0.86))
        for x in range(xa, xb + 1):
            px(d, ox + x, 43, shade(col, 1.3) if (x * 3 + t) % 11 else shade(col, 1.7))
    if r == 2:
        col = shade(lerp(cin, cout, 0.5), 0.8)
        for k in range(6):
            rect(d, ox + 94 + k * 16 / 6, 69 + k, ox + 130 - k * 16 / 6, 69 + k, col)

# ---------------------------------------------------------------- per-room action
def rake_y(tt):
    ph = tt % 20
    return 67 - ph * 37 / 13 if ph < 14 else None

ITEMS = [('rag', 0, 52), ('duck', 3, 38), ('wipe', 8, 58), ('stick', 13, 64), ('rag', 19, 47), ('wipe', 25, 61)]
def _item_plan():
    plan = []
    for kind, sp, y in ITEMS:
        w, h = SIZES[kind]; ym = y + h / 2
        xs = sx(ym) - w - 1
        arrive = sp + math.ceil((xs - 44) / 3.0)
        tp = None
        for tt in range(arrive, arrive + 60):
            ph = tt % 20
            if ph < 14:
                ry = rake_y(tt); prev = rake_y(tt - 1) if ph > 0 else 99
                if ry <= ym < prev: tp = tt; break
        plan.append((kind, sp, y, xs, arrive, tp, tp + (13 - tp % 20)))
    return plan
PLAN = _item_plan()

def r1_items(d, ox, lf):
    dumped = 0
    for kind, sp, y, xs, arrive, tp, ttop in PLAN:
        w, h = SIZES[kind]; rows, pal = ITEM_SPR[kind]
        if lf < sp: continue
        if lf < arrive: pos = (44 + 3.0 * (lf - sp), y + (lf % 2 if kind != 'duck' else 0))
        elif lf < tp:
            pos = (xs, y)
            if kind == 'duck' and lf % 4 < 2: text(d, ox + xs + 2, y - 7, "!", YEL)
        elif lf <= ttop:
            ry = rake_y(lf); pos = (sx(ry) - w - 1, ry - h)
            if kind == 'duck': text(d, ox + pos[0] - 26, pos[1] - 2, "QUACK!", YEL)
        elif lf <= ttop + 4:
            s = (lf - ttop) / 4; pos = (124 + 24 * s, 24 - 28 * s * (1 - s) + 4 * s)
        else:
            dumped += 1; continue
        spr(d, ox + pos[0], pos[1], rows, pal)
    cols = [(206, 196, 176), YEL, WHITE, BROWN, (206, 196, 176), WHITE]
    for k in range(dumped):
        rect(d, ox + 144 + k * 3, 27 - (k % 2), ox + 146 + k * 3, 28, cols[k])

def r1_front(d, ox, lf):
    for y in range(30, 69):
        x = P(sx(y))
        px(d, ox + x, y, STEEL if y % 2 == 0 else CONC_D); px(d, ox + x + 1, y, CONC_D if y % 2 == 0 else GRAY)
    ry = rake_y(lf)
    if ry is not None:
        x = P(sx(ry)); rect(d, ox + x - 3, ry, ox + x - 1, ry, TAN); px(d, ox + x - 3, ry - 1, TAN)

def r2_back(d, ox, lf, t, lc):
    for ring, (R, ry_) in enumerate(((60, 6), (44, 5), (28, 3))):
        for k in range(5):
            a = t * 0.35 * (1 + ring * 0.3) + k * 2 * math.pi / 5
            for da in (0, 0.07, 0.14, 0.21):
                px(d, ox + 112 + R * math.cos(a - da), 53 + ring * 4 + ry_ * math.sin(a - da), lc)
    rect(d, ox + 112, 31, ox + 112, 61, STEEL)
    wv = int(abs(math.cos(t * 0.5)) * 12)
    rect(d, ox + 112 - wv, 61, ox + 112 + wv, 62, TAN)
    settled = 0
    for k in range(28):
        r0 = 18 + (k * 37 % 46); a0 = k * 1.7; delay = k * 1.1
        p = (lf - delay) / 24
        if p <= 0: p = 0
        if p >= 1: settled += 1; continue
        rr = r0 * (1 - p) + 2
        px(d, ox + 112 + rr * math.cos(a0 + lf * 0.45), 48 + p * 25, TAN if k % 2 else (232, 204, 156))
    row = 0
    while settled > 0 and row < 5:
        half = 3 + row * 2; n = min(settled, half * 2 + 1)
        for k in range(n):
            px(d, ox + 112 - half + (k * 5) % (half * 2 + 1), 74 - row, TAN if (k + row) % 3 else (232, 204, 156))
        settled -= n; row += 1

MIC = [(62, 50, 16, 5, 0.21, 0.0), (92, 58, 22, 6, 0.17, 1.0), (122, 51, 20, 5, 0.19, 2.1),
       (152, 58, 18, 6, 0.23, 3.3), (104, 63, 34, 3, 0.15, 4.0), (140, 48, 28, 3, 0.2, 5.2)]
def mic_pos(k, tt):
    bx, by, A, B, w, ph = MIC[k]
    return bx + A * math.sin(tt * w + ph), by + B * math.sin(tt * w * 1.7 + ph * 2), math.cos(tt * w + ph) > 0
_r = random.Random(3)
DOTS = [(_r.randint(48, 176), _r.randint(46, 66)) for _ in range(48)]
EAT = []
for i_, (dx_, dy_) in enumerate(DOTS):
    te = None
    for tt in range(3, H[3]):
        if any(math.hypot(mic_pos(k, tt)[0] - dx_, mic_pos(k, tt)[1] - dy_) < 5.5 for k in range(len(MIC))):
            te = tt; break
    EAT.append(te if te is not None else H[3] - 4 - i_ % 5)

def r3_back(d, ox, lf, t):
    rect(d, ox + 44, 43, ox + 44, 67, GRAY); rect(d, ox + 44, 68, ox + 178, 68, GRAY)
    for j, dx in enumerate(range(54, 180, 16)):
        rect(d, ox + dx, 67, ox + dx + 2, 67, STEEL)
        for k in range(3):
            yy = 66 - ((t * 1.6 + j * 5 + k * 8) % 23)
            xx = dx + 1 + round(math.sin((t + j * 3 + k * 5) * 0.7))
            px(d, ox + xx, yy, (214, 240, 255))
            if yy < 52: px(d, ox + xx + 1, yy, WHITE)
    nom = None
    for i, (x, y) in enumerate(DOTS):
        if EAT[i] > lf: px(d, ox + x, y, (158, 104, 50)); px(d, ox + x + 1, y, (120, 78, 38))
        elif lf - EAT[i] < 3: nom = (x, y)
    for k in range(len(MIC)):
        x, y, right = mic_pos(k, lf)
        rows = MIC_O if (lf + k) % 4 < 2 else MIC_C
        spr(d, ox + x - 2, y - 2, rows if right else flip(rows), {'G': GREEN, 'K': BLACK}, outline=GREEN_DD)
    if nom: text(d, ox + nom[0] - 5, nom[1] - 8, "NOM", GREEN)
    cx, cy = ox + 19, 32
    o = t % 4
    pts = {0: ((-4, 0), (4, 0)), 1: ((-3, -3), (3, 3)), 2: ((0, -4), (0, 4)), 3: ((-3, 3), (3, -3))}[o]
    d.line([cx + pts[0][0], cy + pts[0][1], cx + pts[1][0], cy + pts[1][1]], fill=STEEL)
    pts = {0: ((0, -4), (0, 4)), 1: ((-3, 3), (3, -3)), 2: ((-4, 0), (4, 0)), 3: ((-3, -3), (3, 3))}[o]
    d.line([cx + pts[0][0], cy + pts[0][1], cx + pts[1][0], cy + pts[1][1]], fill=GRAY)
    px(d, cx, cy, GREEN)

def r4_back(d, ox, lf, t):
    for k in range(28):
        x = 46 + (k * 53 % 100); y = 46 + ((k * 7 + t * 0.35) % 15)
        px(d, ox + x, y, FLOC)
        if k % 2: px(d, ox + x + 1, y, FLOC)
    for x in range(42, 183):
        fy = int(floor4(x)); th = 4 + (1 if (x + t // 4) % 7 < 3 else 0)
        rect(d, ox + x, fy - th, ox + x, fy - 1, SLUDGE); px(d, ox + x, fy - th, SLUDGE_L)
    rect(d, ox + 111, 31, ox + 113, 70, STEEL); rect(d, ox + 113, 31, ox + 113, 70, GRAY)
    rect(d, ox + 100, 43, ox + 100, 53, CONC_L); rect(d, ox + 124, 43, ox + 124, 53, CONC_L)
    L = int(abs(math.cos(t * 0.22)) * 62)
    for sgn in (-1, 1):
        for dx in range(2, L + 1):
            x = 112 + sgn * dx; fy = int(floor4(x)); px(d, ox + x, fy - 3, TAN)
            if dx % 8 == 0: rect(d, ox + x, fy - 2, ox + x, fy - 1, CREAM)
    rect(d, ox + 173, 44, ox + 173, 51, CONC_L); rect(d, ox + 173, 51, ox + 182, 51, CONC_L)
    rect(d, ox + 174, 45, ox + 182, 50, shade(C[4], 1.15))
    px(d, ox + 173, 43, WHITE if t % 2 else shade(C[4], 1.5)); px(d, ox + 174, 44, WHITE if t % 2 == 0 else shade(C[4], 1.5))
    px(d, ox + 112, 25, GREEN if (t // 3) % 2 else GREEN_DD)

LAMPY = (46, 51, 56, 61, 66)
GERMS = [(0, 48, 96), (4, 58, 112), (8, 53, 126), (13, 63, 100), (18, 49, 134), (23, 58, 118), (28, 63, 130)]
def r5_back(d, ox, lf, t):
    rect(d, ox + 84, 40, ox + 84, 68, STEEL); rect(d, ox + 150, 40, ox + 150, 68, STEEL)
    for k, y in enumerate(LAMPY):
        for x in range(86, 149, 2):
            off = (t + k) % 2
            px(d, ox + x + off, y - 1, UV_D); px(d, ox + x + 1 - off, y + 1, UV_D)
        rect(d, ox + 86, y, ox + 148, y, UV)
        for x in range(86, 149):
            if (x + t * 2 + k * 3) % 9 < 2: px(d, ox + x, y, UV_L)
    for k, c in enumerate((GREEN, YEL, GREEN, RED, GREEN)):
        px(d, ox + 162 + k * 2, 33, c if (t // 2 + k) % 3 else DARK)
    px(d, ox + 163 + (t % 8), 27 + (t * 3 % 3), GREEN)
    for sp, y, zx in GERMS:
        if lf < sp: continue
        x = 44 + 2.4 * (lf - sp)
        tz = sp + math.ceil((zx - 44) / 2.4); dz = lf - tz
        if x < zx:
            spr(d, ox + x - 2, y - 2 + (lf % 2), GERM if lf % 4 < 2 else GERM2, {'R': RED, 'K': BLACK})
        elif dz < 2:
            ly = min(LAMPY, key=lambda v: abs(v - y))
            d.line([ox + zx + 5, ly, ox + zx + 2, (ly + y) // 2, ox + zx + 4, (ly + y) // 2, ox + zx, y], fill=WHITE)
            spr(d, ox + zx - 2, y - 2, GERM, {'R': WHITE, 'K': UV})
            text(d, ox + zx - 6, y - 9, "ZAP", UV_L)
        elif dz < 6:
            spr(d, ox + zx - 2 + dz, y - 2 + dz, GERM2, {'R': GRAY if dz < 4 else DARK, 'K': BLACK})

def r6_back(d, ox, lf, t):
    for bx, n in ((96, 6), (132, 5), (170, 7), (208, 5)):
        for j in range(n):
            px(d, ox + bx + round(math.sin(t * 0.3 + j * 0.8 + bx) * 1.3 * j / n), 76 - j, GREEN_D)
    rect(d, ox + 112, 75, ox + 120, 76, (30, 70, 96)); rect(d, ox + 150, 74, ox + 156, 76, (30, 70, 96))
    for k, (off, y, c) in enumerate(((0, 63, ORANGE), (60, 70, CREAM), (115, 58, (255, 190, 120)))):
        x = 70 + ((t * 1.3 + off) % 148)
        if x < 214: spr(d, ox + x, y, FISH, {'F': c, 'K': BLACK})
    if 40 <= lf <= 50:
        s = (lf - 40) / 10
        spr(d, ox + 190 + 20 * s, 50 - 44 * s * (1 - s) - 2, FISH, {'F': GREEN, 'K': BLACK})
    for t0, sxx in ((40, 191), (50, 212)):
        if 0 <= lf - t0 < 3:
            for k in (-2, 0, 2): px(d, ox + sxx + k * (lf - t0 + 1), 48 - (lf - t0), WHITE)

def r0_back(d, ox, lf, t):
    g = (70, 58, 22) if t % 9 else (110, 92, 36)
    for dx, dy in ((-2, 0), (2, 0), (0, 2), (-1, 1), (1, 1), (-2, 1), (2, 1)): px(d, ox + 138 + dx, 13 + dy, g)
    if lf < 22 or lf >= 36: rect(d, ox + 158, 30, ox + 167, 31, TW)
    elif lf < 30:
        for x in range(158, 168):
            for y in (30, 31): px(d, ox + x, y, TW if (x + y + lf) % 3 else WHITE)
    else: rect(d, ox + 158, 31, ox + 167, 31, TW)
    hy = 21 + (1 if 22 <= lf < 27 and lf % 2 == 0 else 0)
    rect(d, ox + 167, hy, ox + 169, hy, STEEL)
    pal = {'P': BROWN, 'L': (184, 128, 66), 'W': WHITE, 'K': BLACK, 'M': BROWN_D}
    if lf < 14:
        spr(d, ox + 84 + 62 * lf / 14, 30 - abs(math.sin(lf * math.pi / 3.5)) * 5, POOP, pal, outline=BLACK)
    elif lf < 19:
        s = (lf - 14) / 4
        spr(d, ox + 146 + 11 * s, 30 - 12 * s - 28 * s * (1 - s) + 0, POOP, pal, outline=BLACK)
    elif lf < 22:
        n = (7, 4, 2)[lf - 19]
        spr(d, ox + 157, 28 - n, POOP[:n], pal)
    if 19 <= lf < 23: text(d, ox + 140, 14, "PLOP", CREAM)
    if 23 <= lf < 33: text(d, ox + 142, 14 - (1 if lf % 2 else 0), "FLUSH!", GREEN)

# ---------------------------------------------------------------- hero path
def poly(pts, u):
    u = clamp(u)
    segs = [math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
    s = u * sum(segs)
    for k, L in enumerate(segs):
        if s <= L or k == len(segs) - 1:
            f = clamp(s / L if L else 0); a, b = pts[k], pts[k + 1]
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        s -= L

DEF_PATH = [(12, 60), (42, 60), (64, 50), (112, 48), (160, 50), (182, 60), (212, 60)]
def drop_pos(r, lf):
    """local (x, y) of the hero in room r at hold frame lf, or None if not on screen yet."""
    u = lf / H[r]
    if r == 0:
        if lf < 26: return None
        return poly([(164, 40), (164, 60), (212, 60)], (lf - 26) / (H[0] - 26))
    if r == 2:
        if u < 0.12: return poly([(12, 60), (44, 60), (54, 54)], u / 0.12)
        if u < 0.84:
            v = (u - 0.12) / 0.72; th = math.pi + v * 3 * math.pi; R = 58 - 20 * math.sin(math.pi * v)
            return 112 + R * math.cos(th), 54 + 6 * math.sin(th)
        return poly([(170, 54), (184, 60), (212, 60)], (u - 0.84) / 0.16)
    if r == 6:
        if lf < 10: return 12 + 52 * lf / 10, 60
        if lf < 14: return poly([(64, 60), (76, 57), (84, 50)], (lf - 10) / 4)
        if lf < 30:
            s = (lf - 14) / 16; return 84 + 66 * s, 48 - 104 * s * (1 - s)
        return min(160, 150 + (lf - 30) * 0.35), 47
    return poly(DEF_PATH, u)

def ease(p): return p * p * (3 - 2 * p)
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# ---------------------------------------------------------------- frame
STATIC = build_static()
state = {'drone': 196.0}

def render(r, lf, pp, t, dissolve=0):
    world = STATIC.copy(); d = ImageDraw.Draw(world)
    vis = [r] + ([r + 1] if pp > 0 and r + 1 < NR else [])
    lfs = {r: lf, r + 1: 0}
    for q in vis:
        water(d, q, t, lfs[q]); ox = q * RW
        if q == 0: r0_back(d, ox, lfs[q], t)
        if q == 1: r1_items(d, ox, lfs[q])
        if q == 2: r2_back(d, ox, lfs[q], t, shade(lerp(C[1], C[2], 0.5), 1.35))
        if q == 3: r3_back(d, ox, lfs[q], t)
        if q == 4: r4_back(d, ox, lfs[q], t)
        if q == 5: r5_back(d, ox, lfs[q], t)
        if q == 6: r6_back(d, ox, lfs[q], t)

    # hero
    if pp > 0:
        hx, hy = r * RW + 212 + pp * 24, 60.0
    else:
        p = drop_pos(r, lf)
        hx, hy = (r * RW + p[0], p[1]) if p else (None, None)
    level = r - 1 if r > 0 else 0
    if hx is not None:
        hr = int(hx // RW); xl = hx - hr * RW
        body = shade(watercol(hr, xl), 1.5 if hr < 3 else 1.35)
        in_tank = 1 <= hr <= 5 and 44 < xl < 180
        bob = round(math.sin(t * 0.7)) if in_tank or (hr == 6 and lf >= 30) else 0
        mood = 'grump' if hr <= 2 else ('ok' if hr <= 4 else 'happy')
        shades = (hr == 5 and xl > 74) or hr == 6
        if hr == 6 and 14 <= lf < 30 and pp == 0:
            for k in range(4):
                a = t * 0.9 + k * 1.57
                px(d, hx + 9 * math.cos(a), hy + 8 * math.sin(a), YEL if (t + k) % 2 else WHITE)
        for k in (1, 2, 3):
            if hr >= 1 and (t + k) % 3 == 0: px(d, hx - 5 - k * 3, hy + 2 - k, shade(body, 1.3))
        draw_drop(d, hx, hy + bob, body, mood, shades, t, dizzy=(hr == 2 and in_tank))
        if hr == 5 and 74 < xl < 104: text(d, hx - 18, hy - 15, "SHADES ON", CREAM)
        if 1 <= hr <= 5 and 150 <= xl < 178:
            text(d, hx - 12, hy - 13 - (xl - 150) / 4, "+CLEAN", GREEN)
        if 1 <= hr <= 5 and xl >= 150: level = hr
        if hr > r: level = max(level, r)
        if hr == 6:
            level = 6 if (pp == 0 and lf >= 30) else 5
            for t0, sx_ in ((13, 84), (30, 150)):
                if pp == 0 and 0 <= lf - t0 < 4:
                    k2 = lf - t0
                    for s in (-1, 1):
                        px(d, r * RW + sx_ + s * (2 + k2 * 2), 48 - k2, WHITE)
                        px(d, r * RW + sx_ + s * (1 + k2), 46 - k2 * 2, shade(C[6], 1.5))
    if r == 1 or (pp > 0 and r == 0): r1_front(d, RW, lf if r == 1 else 0)
    if r == 6 and pp == 0:
        if lf >= 42: text(d, r * RW + 84, 12, "LEVEL CLEAR!", GREEN, 2)
        if lf >= 46 and (lf // 4) % 2 == 0: text(d, r * RW + 90, 36, "FLUSH TO CONTINUE", CREAM)

    # drone
    target = hx if hx is not None else 196.0
    if r == 0 and pp == 0: target = max(target, 194.0)
    if r == 6 and pp == 0: target += 16
    state['drone'] += (target - state['drone']) * 0.3
    dx = state['drone']; dy = 23 + round(math.sin(t * 0.4) * 1.5)
    if r == 6 and pp == 0 and lf >= 30: dy += 1
    rot = "RRRR.RRRR" if t % 2 else "..RR.RR.."
    eye = 4 if hx is None else (5 if hx > dx + 1 else (3 if hx < dx - 1 else 4))
    rows = [rot] + [list(x) for x in DRONE]
    rows[1] = DRONE[0]; rows = [rot] + DRONE[:]
    body_rows = [list(x) for x in rows]
    body_rows[3][eye] = 'W'
    spr(d, dx - 4, dy, ["".join(x) for x in body_rows], {'G': GREEN, 'K': BLACK, 'W': WHITE, 'S': STEEL, 'R': STEEL},
        outline=BLACK)
    scanning = hx is not None and pp == 0 and 1 <= r <= 5 and lf < H[r] * 0.55
    if scanning:
        for y in range(dy + 8, 43):
            if (y + t) % 2 == 0: px(d, dx + round(math.sin((y + t) * 0.8)), y, GREEN_D)

    cam = P(r * RW + ease(pp) * RW)
    fr = Image.new('RGB', (FW, FH), BG)
    fr.paste(world.crop((cam, 0, cam + RW, SH)), (0, TOP))
    f = ImageDraw.Draw(fr)
    if dissolve:
        for y in range(TOP, TOP + SH):
            for x in range(FW):
                if BAYER[y % 4][x % 4] < dissolve: f.point((x, y), fill=BG)

    # drone readout bubble (screen space)
    msg = ""
    if pp == 0 and not dissolve:
        if r == 0: msg = "ZZZ" if lf < 22 else ("!" if lf < 30 else "")
        elif r == 6: msg = READOUT[6] if lf >= 34 else ""
        elif scanning: msg = "SCAN" + "." * (1 + (t // 3) % 3)
        else: msg = READOUT[r]
    if msg:
        bw = 4 * len(msg) + 4 + (2 if '~' in msg else 0); sxp = P(dx - cam); bx = sxp + 8
        if bx + bw > FW - 2: bx = sxp - 8 - bw
        by = TOP + dy - 1
        f.rectangle([bx, by, bx + bw, by + 8], fill=PANEL, outline=GREEN_D)
        text(f, bx + 3, by + 2, msg, GREEN if '~' in msg or msg == '!' else CREAM)

    # HUD
    cur = r + 1 if pp > 0.5 else r
    f.rectangle([0, 0, FW - 1, TOP - 1], fill=PANEL); f.rectangle([0, TOP - 1, FW - 1, TOP - 1], fill=GREEN_DD)
    f.rectangle([2, 3, 6, 7], fill=GREEN)
    text(f, 9, 3, "EFFLUENT", CREAM); text(f, 44, 3, "//", GRAYD)
    x = 55
    for k, tk in enumerate(["IN", "SCR", "GRT", "AER", "CLR", "DIS", "OUT"]):
        text(f, x, 3, tk, GREEN if k == cur else (GREEN_D if k < cur else GRAYD)); x += 4 * len(tk)
        if k < 6: text(f, x, 3, ">", GREEN_D if k < cur else GRAYD); x += 4
    text(f, 165, 3, "CLEAN", CREAM)
    for s in range(6):
        f.rectangle([188 + s * 6, 3, 192 + s * 6, 7], fill=GREEN if s < level else DARK)

    # caption
    f.rectangle([0, 88, FW - 1, FH - 1], fill=PANEL); f.rectangle([0, 88, FW - 1, 88], fill=GREEN_DD)
    text(f, 4, 92, ">", GREEN)
    shown = "" if (pp > 0 or dissolve) else CAPTIONS[r][:lf * 3]
    text(f, 10, 92, shown, CREAM)
    if (t // 3) % 2 == 0: f.rectangle([10 + 4 * len(shown), 92, 12 + 4 * len(shown), 96], fill=GREEN)
    return fr

def timeline():
    seq = []
    for r in range(NR):
        for lf in range(H[r]): seq.append((r, lf, 0.0, 0))
        if r < NR - 1:
            for p in range(PAN): seq.append((r, H[r], (p + 1) / (PAN + 1), 0))
    for lv in (3, 6, 9, 12, 16, 16): seq.append((6, H[6] - 1, 0.0, lv))
    for lv in (12, 8, 4): seq.append((0, 0, 0.0, lv))
    return seq

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "frames"
    os.makedirs(out, exist_ok=True)
    for f_ in os.listdir(out): os.remove(os.path.join(out, f_))
    seq = timeline()
    for t, (r, lf, pp, dis) in enumerate(seq):
        if dis and r == 0: state['drone'] = 196.0
        im = render(r, lf, pp, t, dis)
        im.resize((FW * SCALE, FH * SCALE), Image.NEAREST).save(os.path.join(out, f"f{t:04d}.png"))
    print(len(seq), "frames")
