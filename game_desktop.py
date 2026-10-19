"""
DOSA DASH 2D  -  Kitchen Escape
================================
A dosa sits on a kitchen counter. A human hand reaches for it, so it RUNS.
Jump over the cookware. Hit anything and the hand catches you.
Catch CHUTNEY to become immune - while immune you smash straight through obstacles.

Put your artwork in  assets/dosa.png  and  assets/chutney.png  (transparent PNGs).
If they are missing, the game draws a simple fallback so it always runs.

Run:   python main.py
"""
import math
import random
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SAVE_FILE = ROOT / "highscore.txt"

# --------------------------------------------------------------------------
# Tunable constants
# --------------------------------------------------------------------------
W, H = 1280, 720
FPS = 60

COUNTER_BACK_Y = 548     # back edge of the counter top (where the wall ends)
GROUND_Y = 596           # the line the dosa and obstacles stand on
COUNTER_FRONT_Y = 612    # front edge of the counter top
DOSA_X = 330             # fixed screen x of the dosa

GRAVITY = 2700.0
JUMP_V = 1100.0          # upward speed of a jump (px/s)
COYOTE_TIME = 0.08       # can still jump this long after leaving the ground
JUMP_BUFFER = 0.12       # a jump pressed slightly early still counts

BASE_SPEED = 360.0       # px/s
MAX_SPEED = 740.0
SPEED_PER_METER = 2.4

IMMUNITY_TIME = 4.0      # seconds of immunity per chutney
IMMUNITY_MAX = 8.0
CHUTNEY_CHANCE = 0.25    # chance that an obstacle has a chutney above it

DOSA_HEIGHT = 112        # drawn height of the dosa sprite (px)
CHUTNEY_HEIGHT = 58

WALL_PERIOD = 1536       # width of the repeating background layer
WALL_PARALLAX = 0.3

# Intro / death timelines (seconds)
INTRO_SCARE_AT = 0.9
INTRO_RUN_AT = 1.6
INTRO_SLAM_AT = 1.85
INTRO_END = 2.7
DEATH_END = 2.1

HAND_START = (-220.0, -320.0)
HAND_HOVER = (DOSA_X - 120.0, GROUND_Y - 250.0)
HAND_SLAM = (DOSA_X - 170.0, GROUND_Y - 6.0)
HAND_EXIT = (-320.0, -360.0)
HAND_ANCHOR = (95, 385)  # fingertip point inside the hand image

SKIN = (240, 190, 150)
SKIN_D = (190, 130, 95)
SLEEVE = (70, 110, 170)
SLEEVE_D = (45, 75, 125)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    t = clamp(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = clamp(t, 0.0, 1.0)
    return t ** 3


def ease_in_out(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def rounded(surf, color, rect, radius=12, outline=None, width=3):
    rect = pygame.Rect(rect)
    if outline:
        pygame.draw.rect(surf, outline, rect, border_radius=radius)
        inner = rect.inflate(-width * 2, -width * 2)
        pygame.draw.rect(surf, color, inner, border_radius=max(0, radius - width))
    else:
        pygame.draw.rect(surf, color, rect, border_radius=radius)


def draw_panel(surf, rect, color=(20, 28, 26), alpha=170, radius=18, outline=None):
    rect = pygame.Rect(rect)
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (color[0], color[1], color[2], alpha), s.get_rect(), border_radius=radius)
    if outline:
        pygame.draw.rect(s, outline, s.get_rect(), 3, border_radius=radius)
    surf.blit(s, rect.topleft)


def draw_text(surf, text, font, color, pos, anchor="center", shadow=(30, 20, 10)):
    img = font.render(text, True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    if shadow:
        surf.blit(font.render(text, True, shadow), rect.move(3, 3))
    surf.blit(img, rect)
    return rect


def make_font(size):
    return pygame.font.SysFont("arialrounded,arialblack,verdana,arial", size, bold=True)


def load_best():
    try:
        return int(SAVE_FILE.read_text().strip())
    except Exception:
        return 0


def save_best(value):
    try:
        SAVE_FILE.write_text(str(int(value)))
    except Exception:
        pass


# --------------------------------------------------------------------------
# Asset loading (your PNGs) with procedural fallbacks
# --------------------------------------------------------------------------
def remove_flat_background(img):
    """If a PNG has no transparency but a flat-colour background, make the
    background (connected to the corners) transparent."""
    try:
        w, h = img.get_size()
        corners = [img.get_at((0, 0)), img.get_at((w - 1, 0)),
                   img.get_at((0, h - 1)), img.get_at((w - 1, h - 1))]
        if any(c.a < 250 for c in corners):
            return img  # already transparent
        base = corners[0]
        for c in corners:
            if abs(c.r - base.r) > 12 or abs(c.g - base.g) > 12 or abs(c.b - base.b) > 12:
                return img
        bg = pygame.mask.from_threshold(img, (base.r, base.g, base.b, 255), (24, 24, 24, 255))
        bg = bg.connected_component((0, 0))
        if bg.count() < w * h * 0.05:
            return img
        fg = bg.copy()
        fg.invert()
        out = fg.to_surface(setsurface=img, unsetcolor=(0, 0, 0, 0))
        return out.convert_alpha()
    except Exception as e:
        print("Background clean-up skipped:", e)
        return img


def load_sprite(name, target_h):
    path = ASSETS / name
    if not path.is_file():
        print("[assets] %s not found - using fallback art" % path)
        return None
    try:
        img = pygame.image.load(str(path)).convert_alpha()
        img = remove_flat_background(img)
        box = img.get_bounding_rect(1)       # crop transparent padding
        if box.width > 0 and box.height > 0:
            img = img.subsurface(box).copy()
        scale = target_h / float(img.get_height())
        size = (max(1, int(img.get_width() * scale)), int(target_h))
        return pygame.transform.smoothscale(img, size)
    except Exception as e:
        print("[assets] could not load %s: %s" % (path, e))
        return None


def fallback_dosa(h):
    w = int(h * 1.2)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    body = pygame.Rect(0, int(h * 0.10), w, int(h * 0.90))
    pygame.draw.ellipse(s, (120, 70, 25), body)
    pygame.draw.ellipse(s, (226, 156, 62), body.inflate(-8, -8))
    pygame.draw.ellipse(s, (246, 196, 110), body.inflate(-36, -30))
    for ex in (0.36, 0.64):
        pygame.draw.circle(s, (255, 255, 255), (int(w * ex), int(h * 0.50)), 11)
        pygame.draw.circle(s, (30, 20, 15), (int(w * ex) + 2, int(h * 0.50)), 6)
    pygame.draw.arc(s, (110, 50, 30), (int(w * 0.38), int(h * 0.52), int(w * 0.24), int(h * 0.22)),
                    math.pi * 1.1, math.pi * 1.9, 4)
    return s


def fallback_chutney(h):
    w = int(h * 1.15)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (150, 120, 80), (0, int(h * 0.35), w, int(h * 0.65)))
    pygame.draw.ellipse(s, (240, 228, 200), (3, int(h * 0.38), w - 6, int(h * 0.58)))
    pygame.draw.ellipse(s, (90, 170, 80), (int(w * 0.12), int(h * 0.28), int(w * 0.76), int(h * 0.42)))
    pygame.draw.ellipse(s, (130, 205, 110), (int(w * 0.28), int(h * 0.34), int(w * 0.30), int(h * 0.14)))
    return s


# --------------------------------------------------------------------------
# Obstacle art (drawn with shapes). Each returns (surface, hit_rect_in_surface)
# --------------------------------------------------------------------------
def art_pot():
    s = pygame.Surface((130, 100), pygame.SRCALPHA)
    steel, dark = (170, 182, 188), (96, 108, 116)
    rounded(s, steel, (16, 14, 98, 86), 10, dark)
    rounded(s, (205, 214, 218), (10, 6, 110, 18), 8, dark)
    rounded(s, (140, 152, 160), (0, 34, 18, 14), 6, dark)
    rounded(s, (140, 152, 160), (112, 34, 18, 14), 6, dark)
    pygame.draw.rect(s, (232, 240, 242), (28, 32, 10, 52), border_radius=5)
    return s, pygame.Rect(14, 8, 102, 92)


def art_plates():
    s = pygame.Surface((124, 58), pygame.SRCALPHA)
    for i in range(4):
        y = 40 - 12 * i
        rim = (120, 170, 210) if i % 2 else (236, 240, 236)
        pygame.draw.ellipse(s, (130, 150, 160), (4, y, 116, 18))
        pygame.draw.ellipse(s, rim, (6, y + 1, 112, 15))
    pygame.draw.ellipse(s, (250, 250, 244), (26, 6, 72, 10))
    return s, pygame.Rect(8, 6, 108, 52)


def art_jars():
    s = pygame.Surface((96, 92), pygame.SRCALPHA)
    for x, col, lid in ((4, (222, 140, 70), (80, 130, 100)), (50, (190, 70, 60), (240, 200, 100))):
        rounded(s, col, (x, 24, 42, 66), 10, (90, 55, 35))
        rounded(s, lid, (x + 3, 8, 36, 20), 6, (70, 60, 40))
        pygame.draw.rect(s, (250, 240, 220), (x + 8, 44, 26, 22), border_radius=4)
    return s, pygame.Rect(4, 8, 88, 84)


def art_kettle():
    s = pygame.Surface((132, 118), pygame.SRCALPHA)
    steel, dark = (178, 190, 196), (96, 108, 116)
    pygame.draw.polygon(s, dark, [(98, 66), (126, 36), (132, 46), (108, 90)])
    pygame.draw.arc(s, dark, (0, 32, 58, 66), math.pi / 2, 3 * math.pi / 2, 8)
    pygame.draw.ellipse(s, dark, (12, 34, 96, 82))
    pygame.draw.ellipse(s, steel, (16, 38, 88, 74))
    rounded(s, (140, 152, 160), (38, 22, 44, 16), 7, dark)
    pygame.draw.circle(s, dark, (60, 18), 7)
    pygame.draw.ellipse(s, (236, 244, 246), (28, 50, 18, 36))
    return s, pygame.Rect(14, 16, 92, 102)


def art_tomato():
    s = pygame.Surface((70, 66), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (140, 28, 24), (4, 10, 62, 56))
    pygame.draw.ellipse(s, (218, 58, 44), (7, 13, 56, 50))
    pygame.draw.ellipse(s, (250, 140, 120), (16, 20, 14, 10))
    pygame.draw.polygon(s, (50, 130, 60), [(35, 8), (26, 0), (32, 12), (20, 12), (31, 17),
                                           (35, 26), (39, 17), (50, 12), (38, 12), (44, 0)])
    return s, pygame.Rect(8, 10, 54, 56)


def art_pin():
    s = pygame.Surface((150, 34), pygame.SRCALPHA)
    wood, dark = (214, 164, 98), (140, 94, 50)
    rounded(s, wood, (22, 4, 106, 26), 10, dark)
    rounded(s, (190, 140, 80), (0, 10, 28, 14), 6, dark)
    rounded(s, (190, 140, 80), (122, 10, 28, 14), 6, dark)
    return s, pygame.Rect(6, 4, 138, 30)


OBSTACLE_BUILDERS = {
    "plate": art_plates, "veg": art_tomato, "pot": art_pot,
    "jar": art_jars, "kettle": art_kettle, "pin": art_pin,
}
OBSTACLE_KINDS = ["plate", "veg", "pot", "jar", "kettle", "pin"]
OBSTACLE_COLORS = {
    "plate": (236, 240, 236), "veg": (218, 58, 44), "pot": (170, 182, 188),
    "jar": (222, 140, 70), "kettle": (178, 190, 196), "pin": (214, 164, 98),
}


# --------------------------------------------------------------------------
# Hand art
# --------------------------------------------------------------------------
def build_hand(curl):
    w, h = 190, 400
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx = w // 2
    rounded(s, SLEEVE, (cx - 70, 0, 140, 110), 14, SLEEVE_D, 4)
    rounded(s, (235, 235, 240), (cx - 72, 96, 144, 26), 8, (170, 170, 180), 3)
    rounded(s, SKIN, (cx - 52, 120, 104, 100), 20, SKIN_D, 4)
    for i, length in enumerate((78, 96, 102, 88)):
        fx = cx - 58 + i * 30
        ln = int(length * (1 - 0.55 * curl))
        rounded(s, SKIN, (fx, 270, 28, ln + 20), 14, SKIN_D, 3)
    rounded(s, SKIN, (cx - 86, 215, 32, 74 - int(20 * curl)), 16, SKIN_D, 3)
    rounded(s, SKIN, (cx - 62, 190, 124, 100), 30, SKIN_D, 4)
    return s


def draw_hand(surf, frames, tip_x, tip_y, angle, curl):
    img = frames[int(round(clamp(curl, 0.0, 1.0) * (len(frames) - 1)))]
    rot = pygame.transform.rotate(img, angle)
    vx = HAND_ANCHOR[0] - img.get_width() / 2.0
    vy = HAND_ANCHOR[1] - img.get_height() / 2.0
    a = math.radians(angle)
    rx = vx * math.cos(a) + vy * math.sin(a)
    ry = -vx * math.sin(a) + vy * math.cos(a)
    surf.blit(rot, rot.get_rect(center=(int(tip_x - rx), int(tip_y - ry))))


def intro_hand_pose(t):
    """Hand reaches in from the top-left, hovers, then slams the counter (and misses)."""
    if t < 0 or t >= INTRO_END:
        return None
    if t < 1.1:
        p = ease_out(t / 1.1)
        return (lerp(HAND_START[0], HAND_HOVER[0], p), lerp(HAND_START[1], HAND_HOVER[1], p),
                lerp(35, 16, p), 0.0)
    if t < INTRO_RUN_AT:
        w = t - 1.1
        return (HAND_HOVER[0] + math.sin(w * 14) * 8, HAND_HOVER[1] + math.sin(w * 9) * 6,
                16, 0.5 + 0.5 * math.sin(w * 16))
    if t < INTRO_SLAM_AT:
        p = ease_in((t - INTRO_RUN_AT) / (INTRO_SLAM_AT - INTRO_RUN_AT))
        return (lerp(HAND_HOVER[0], HAND_SLAM[0], p), lerp(HAND_HOVER[1], HAND_SLAM[1], p),
                lerp(16, 8, p), 0.0)
    p = ease_in((t - INTRO_SLAM_AT) / (INTRO_END - INTRO_SLAM_AT))
    return (lerp(HAND_SLAM[0], HAND_EXIT[0], p), lerp(HAND_SLAM[1], HAND_EXIT[1], p),
            lerp(8, 35, p), 0.0)


def death_hand_pose(t, target):
    """Hand drops from above, grabs the dosa and carries it off. Returns None when not visible."""
    if t < 0.15 or t >= DEATH_END:
        return None
    tx, ty = target
    if t < 0.8:
        p = ease_in_out((t - 0.15) / 0.65)
        return (tx, lerp(-320, ty, p), 6, 0.0)
    if t < 1.05:
        return (tx, ty, 6, (t - 0.8) / 0.25)
    p = ease_in((t - 1.05) / (DEATH_END - 1.05))
    return (lerp(tx, tx + 160, p), lerp(ty, -380, p), lerp(6, 28, p), 1.0)


# --------------------------------------------------------------------------
# Background
# --------------------------------------------------------------------------
def build_wall_layer():
    """Pre-rendered, horizontally repeating kitchen wall (cabinets, tiles, window, fridge)."""
    surf = pygame.Surface((WALL_PERIOD, COUNTER_BACK_Y))
    surf.fill((240, 214, 184))

    # tiled backsplash
    top = 240
    pygame.draw.rect(surf, (219, 196, 166), (0, top, WALL_PERIOD, COUNTER_BACK_Y - top))
    tile_w, tile_h = 96, 48
    rows = (COUNTER_BACK_Y - top) // tile_h + 1
    for r in range(rows):
        off = 0 if r % 2 == 0 else tile_w // 2
        for c in range(-1, WALL_PERIOD // tile_w + 1):
            rect = pygame.Rect(c * tile_w + off + 2, top + r * tile_h + 2, tile_w - 4, tile_h - 4)
            pygame.draw.rect(surf, (250, 238, 220), rect, border_radius=6)
            pygame.draw.line(surf, (255, 249, 238), (rect.left + 6, rect.top + 3), (rect.right - 6, rect.top + 3), 2)
    pygame.draw.rect(surf, (196, 160, 128), (0, top - 12, WALL_PERIOD, 12))

    # upper cabinets (slot 2 = window, slot 5 = fridge)
    sage, sage_d = (108, 156, 132), (70, 112, 92)
    for i in range(WALL_PERIOD // 192):
        x0 = i * 192
        if i in (2, 5):
            continue
        rounded(surf, sage, (x0 + 6, 24, 180, 196), 8, sage_d, 4)
        rounded(surf, (132, 178, 152), (x0 + 20, 40, 152, 164), 6, (80, 126, 104), 3)
        pygame.draw.circle(surf, (232, 186, 98), (x0 + 156, 188), 7)

    # window
    wx = 2 * 192
    rounded(surf, (250, 246, 238), (wx + 20, 36, 152, 176), 8, (190, 175, 150), 4)
    pygame.draw.rect(surf, (176, 214, 236), (wx + 34, 50, 124, 148))
    pygame.draw.ellipse(surf, (255, 255, 255), (wx + 44, 70, 60, 26))
    pygame.draw.ellipse(surf, (255, 255, 255), (wx + 80, 84, 56, 22))
    pygame.draw.line(surf, (250, 246, 238), (wx + 96, 50), (wx + 96, 198), 6)
    pygame.draw.line(surf, (250, 246, 238), (wx + 34, 124), (wx + 158, 124), 6)

    # fridge
    fx = 5 * 192
    rounded(surf, (190, 210, 214), (fx + 8, 40, 176, COUNTER_BACK_Y), 14, (130, 150, 156), 4)
    pygame.draw.line(surf, (130, 150, 156), (fx + 12, 190), (fx + 180, 190), 4)
    rounded(surf, (110, 130, 136), (fx + 156, 70, 10, 90), 5)
    rounded(surf, (110, 130, 136), (fx + 156, 210, 10, 130), 5)
    pygame.draw.rect(surf, (230, 90, 70), (fx + 40, 240, 26, 26), border_radius=4)
    pygame.draw.rect(surf, (250, 210, 90), (fx + 80, 260, 26, 26), border_radius=4)
    pygame.draw.rect(surf, (90, 160, 210), (fx + 50, 290, 26, 26), border_radius=4)

    # pendant lamps
    for lx in (180, 800):
        pygame.draw.line(surf, (60, 52, 46), (lx, 0), (lx, 72), 4)
        pygame.draw.polygon(surf, (190, 130, 50), [(lx - 32, 72), (lx + 32, 72), (lx + 52, 116), (lx - 52, 116)])
        pygame.draw.polygon(surf, (255, 196, 102), [(lx - 28, 75), (lx + 28, 75), (lx + 46, 112), (lx - 46, 112)])
        pygame.draw.ellipse(surf, (255, 242, 190), (lx - 26, 108, 52, 14))

    # things standing on the back of the counter
    pygame.draw.polygon(surf, (60, 130, 80), [(80, 470), (40, 410), (70, 440), (80, 395), (95, 440), (125, 405), (110, 470)])
    pygame.draw.ellipse(surf, (80, 160, 95), (50, 420, 90, 60))
    rounded(surf, (214, 108, 72), (50, 488, 80, 60), 10, (150, 70, 45), 3)
    rounded(surf, (180, 190, 190), (690, 484, 52, 64), 8, (110, 120, 120), 3)
    for k in range(4):
        pygame.draw.line(surf, (210, 214, 214), (700 + k * 11, 484), (694 + k * 15, 436), 4)
        pygame.draw.circle(surf, (200, 205, 205), (694 + k * 15, 434), 8)
    for k, (cw, chh, col) in enumerate(((54, 70, (232, 214, 170)), (54, 94, (214, 190, 150)), (54, 56, (240, 226, 190)))):
        rounded(surf, col, (1280 + k * 62, COUNTER_BACK_Y - chh, cw, chh), 8, (160, 135, 95), 3)
        rounded(surf, (130, 100, 70), (1280 + k * 62, COUNTER_BACK_Y - chh, cw, 14), 6)
    return surf


def make_crumbs():
    rng = random.Random(7)
    return [(rng.uniform(0, W), rng.uniform(COUNTER_BACK_Y + 16, COUNTER_FRONT_Y - 6), rng.choice((2, 2, 3)))
            for _ in range(40)]


# --------------------------------------------------------------------------
# Game objects
# --------------------------------------------------------------------------
class Obstacle:
    def __init__(self, kind, x, art):
        self.kind = kind
        self.surf, self.hit_local = art
        self.x = float(x)
        self.w = self.surf.get_width()
        self.y = GROUND_Y - self.surf.get_height()

    @property
    def hit(self):
        return pygame.Rect(int(self.x) + self.hit_local.x, int(self.y) + self.hit_local.y,
                           self.hit_local.width, self.hit_local.height)


class Chutney:
    def __init__(self, x, y):
        self.x = float(x)
        self.base_y = float(y)
        self.phase = random.uniform(0, 6.28)
        self.y = float(y)


# --------------------------------------------------------------------------
# The game
# --------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("DOSA DASH 2D  |  Kitchen Escape")
        self.clock = pygame.time.Clock()
        self.canvas = pygame.Surface((W, H))

        self.f_title = make_font(112)
        self.f_big = make_font(64)
        self.f_med = make_font(40)
        self.f_small = make_font(28)
        self.f_tiny = make_font(22)

        self.dosa_img = load_sprite("dosa.png", DOSA_HEIGHT) or fallback_dosa(DOSA_HEIGHT)
        self.chutney_img = load_sprite("chutney.png", CHUTNEY_HEIGHT) or fallback_chutney(CHUTNEY_HEIGHT)
        self.chutney_icon = pygame.transform.smoothscale(
            self.chutney_img,
            (max(1, int(self.chutney_img.get_width() * 34.0 / self.chutney_img.get_height())), 34))
        self.halo = pygame.Surface((110, 110), pygame.SRCALPHA)
        pygame.draw.circle(self.halo, (170, 255, 150, 70), (55, 55), 54)

        self.obstacle_art = {k: b() for k, b in OBSTACLE_BUILDERS.items()}
        self.wall = build_wall_layer()
        self.hand_frames = [build_hand(i / 4.0) for i in range(5)]
        self.crumbs = make_crumbs()

        self.best = load_best()
        self.running = True
        self.state = "menu"
        self.reset_world()

    # ------------------------------------------------------------------
    def reset_world(self):
        self.scroll = 0.0
        self.cur_speed = 0.0
        self.h = 0.0                 # dosa height above the counter
        self.vy = 0.0                # upward velocity
        self.on_ground = True
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.run_t = 0.0
        self.play_t = 0.0
        self.obstacles = []
        self.chutneys = []
        self.particles = []
        self.floaters = []
        self.chutney_count = 0
        self.smashed = 0
        self.shield_t = 0.0
        self.intro_t = 0.0
        self.death_t = 0.0
        self.shake = 0.0
        self.slam_done = False
        self.spawn_cursor = 900.0
        self.final_score = 0
        self.new_best = False

    @property
    def meters(self):
        return int(self.scroll / 100.0)

    @property
    def score(self):
        return self.meters + self.chutney_count * 10 + self.smashed * 5

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.state in ("playing", "paused"):
                        self.toggle_pause()
                    elif self.state in ("menu", "over"):
                        self.running = False
                elif e.key == pygame.K_p:
                    self.toggle_pause()
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.start_or_restart()
                elif e.key == pygame.K_r:
                    if self.state in ("over", "paused"):
                        self.start_intro()
                elif e.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    self.press_jump()
            elif e.type == pygame.KEYUP:
                if e.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    self.release_jump()
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.press_jump()
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self.release_jump()

    def start_or_restart(self):
        if self.state in ("menu", "over"):
            self.start_intro()

    def press_jump(self):
        if self.state in ("menu", "over"):
            self.start_intro()
        elif self.state == "playing":
            self.jump_buffer = JUMP_BUFFER

    def release_jump(self):
        if self.state == "playing" and self.vy > 420:
            self.vy *= 0.45           # let go early = shorter hop

    def toggle_pause(self):
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"

    # ------------------------------------------------------------------
    # State changes
    # ------------------------------------------------------------------
    def start_intro(self):
        self.reset_world()
        self.state = "intro"

    def begin_run(self):
        self.state = "playing"
        self.vy = 800.0               # the dosa leaps away in fright
        self.h = 0.5
        self.on_ground = False

    def start_death(self):
        self.state = "dying"
        self.death_t = 0.0
        self.cur_speed = 0.0
        self.shield_t = 0.0
        self.final_score = self.score
        if self.final_score > self.best:
            self.best = self.final_score
            self.new_best = True
            save_best(self.best)
        self.shake = 0.35
        r = self.dosa_rect()
        self.burst(r.centerx, r.centery, (250, 200, 90), 16, 320)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt):
        self.shake = max(0.0, self.shake - dt)
        self.update_particles(dt)
        if self.state == "menu":
            self.run_t += dt
        elif self.state == "intro":
            self.run_t += dt
            self.intro_t += dt
            self.update_hand_events()
            if self.intro_t >= INTRO_RUN_AT:
                self.begin_run()
        elif self.state == "playing":
            self.update_playing(dt)
        elif self.state == "dying":
            self.death_t += dt
            self.step_vertical(dt)
            if self.death_t >= DEATH_END:
                self.state = "over"

    def update_hand_events(self):
        if not self.slam_done and self.intro_t >= INTRO_SLAM_AT:
            self.slam_done = True
            self.shake = 0.3
            for _ in range(14):
                self.particles.append(self.make_particle(HAND_SLAM[0] - self.scroll, GROUND_Y - 4,
                                                         (226, 200, 160), 260, up=True))

    def step_vertical(self, dt):
        if self.h > 0 or self.vy > 0:
            self.vy -= GRAVITY * dt
            self.h += self.vy * dt
            if self.h <= 0:
                self.h = 0.0
                self.vy = 0.0
                if not self.on_ground:
                    for _ in range(5):
                        self.particles.append(self.make_particle(DOSA_X, GROUND_Y - 2, (226, 200, 160), 120, up=True))
                self.on_ground = True
            else:
                self.on_ground = False
        else:
            self.on_ground = True

    def update_playing(self, dt):
        self.run_t += dt
        self.play_t += dt
        if self.intro_t < INTRO_END:
            self.intro_t += dt
            self.update_hand_events()

        target = min(MAX_SPEED, BASE_SPEED + self.meters * SPEED_PER_METER)
        self.cur_speed = min(target, self.cur_speed + 800.0 * dt)
        dx = self.cur_speed * dt
        self.scroll += dx

        # jump handling (with a little forgiveness)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.coyote = COYOTE_TIME if self.on_ground else max(0.0, self.coyote - dt)
        if self.jump_buffer > 0 and (self.on_ground or self.coyote > 0):
            self.vy = JUMP_V
            self.h = max(self.h, 0.5)
            self.on_ground = False
            self.coyote = 0.0
            self.jump_buffer = 0.0
        self.step_vertical(dt)

        self.shield_t = max(0.0, self.shield_t - dt)

        # spawn ahead of the dosa
        self.spawn_cursor -= dx
        while self.spawn_cursor < W + 400:
            self.spawn_group()

        dr = self.dosa_rect()

        for o in list(self.obstacles):
            o.x -= dx
            if o.x + o.w < -60:
                self.obstacles.remove(o)
                continue
            if dr.colliderect(o.hit):
                if self.shield_t > 0:
                    self.smash(o)
                else:
                    self.start_death()
                    return

        for c in list(self.chutneys):
            c.x -= dx
            c.y = c.base_y + math.sin(self.run_t * 4 + c.phase) * 6
            if c.x < -60:
                self.chutneys.remove(c)
                continue
            pick = pygame.Rect(int(c.x) - 26, int(c.y) - 26, 52, 52)
            if dr.inflate(16, 16).colliderect(pick):
                self.chutneys.remove(c)
                self.collect(c)

    def spawn_group(self):
        speed = max(self.cur_speed, BASE_SPEED)
        gap = random.uniform(0.8, 1.25) * speed * 0.8 + 260
        x = self.spawn_cursor + gap
        kind = random.choice(OBSTACLE_KINDS)
        o = self.add_obstacle(kind, x)
        right = o.x + o.w
        # Tomato pairs need a longer jump window, so they only appear once the game is fast.
        if kind == "veg" and speed >= 520 and random.random() < 0.3:
            o2 = self.add_obstacle("veg", right + random.uniform(20, 40))
            right = o2.x + o2.w
        if random.random() < CHUTNEY_CHANCE:
            cy = GROUND_Y - min(o.hit_local.height + 80, 190)
            self.chutneys.append(Chutney(o.x + o.w / 2.0, cy))
        elif random.random() < 0.2:
            self.chutneys.append(Chutney((self.spawn_cursor + x) / 2.0, GROUND_Y - 42))
        self.spawn_cursor = right

    def add_obstacle(self, kind, x):
        o = Obstacle(kind, x, self.obstacle_art[kind])
        self.obstacles.append(o)
        return o

    def collect(self, c):
        self.chutney_count += 1
        self.shield_t = min(IMMUNITY_MAX, self.shield_t + IMMUNITY_TIME)
        self.burst(c.x, c.y, (120, 230, 120), 14, 260)
        self.floaters.append([ "IMMUNE!", c.x, c.y - 30, 1.0, (150, 255, 160)])

    def smash(self, o):
        self.obstacles.remove(o)
        self.smashed += 1
        self.shake = 0.18
        self.burst(o.x + o.w / 2.0, o.y + o.surf.get_height() / 2.0, OBSTACLE_COLORS[o.kind], 22, 420)
        self.floaters.append(["SMASH!", o.x + o.w / 2.0, o.y - 10, 0.8, (255, 230, 120)])

    def dosa_rect(self):
        sw, sh = self.dosa_img.get_size()
        r = pygame.Rect(0, 0, int(sw * 0.55), int(sh * 0.72))
        r.midbottom = (DOSA_X, int(GROUND_Y - self.h) - 4)
        return r

    # particles ----------------------------------------------------------
    def make_particle(self, x, y, color, speed, up=False):
        ang = random.uniform(math.pi * 1.1, math.pi * 1.9) if up else random.uniform(0, math.tau)
        sp = random.uniform(0.3, 1.0) * speed
        return {"x": x, "y": y, "vx": math.cos(ang) * sp, "vy": math.sin(ang) * sp,
                "life": random.uniform(0.35, 0.8), "size": random.randint(3, 7), "color": color}

    def burst(self, x, y, color, n, speed):
        for _ in range(n):
            self.particles.append(self.make_particle(x, y, color, speed))

    def update_particles(self, dt):
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 900.0 * dt
            p["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0]
        for f in self.floaters:
            f[2] -= 50 * dt
            f[3] -= dt
        self.floaters = [f for f in self.floaters if f[3] > 0]

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self):
        c = self.canvas
        self.draw_wall(c)
        self.draw_counter(c)
        self.draw_actors(c)
        self.draw_particles(c)
        self.draw_hud(c)
        self.draw_overlays(c)

        offset = (0, 0)
        if self.shake > 0:
            m = int(min(self.shake, 0.4) * 30)
            offset = (random.randint(-m, m), random.randint(-m, m))
        self.screen.fill((0, 0, 0))
        self.screen.blit(c, offset)
        pygame.display.flip()

    def draw_wall(self, c):
        x = -int((self.scroll * WALL_PARALLAX) % WALL_PERIOD)
        c.blit(self.wall, (x, 0))
        c.blit(self.wall, (x + WALL_PERIOD, 0))

    def draw_counter(self, c):
        pygame.draw.rect(c, (236, 206, 166), (0, COUNTER_BACK_Y, W, COUNTER_FRONT_Y - COUNTER_BACK_Y))
        pygame.draw.rect(c, (214, 182, 142), (0, COUNTER_BACK_Y, W, 10))
        x = -int(self.scroll % 192)
        while x < W:
            pygame.draw.line(c, (214, 184, 146), (x, COUNTER_BACK_Y + 10), (x, COUNTER_FRONT_Y), 3)
            x += 192
        for cx, cy, r in self.crumbs:
            pygame.draw.circle(c, (200, 165, 120), (int((cx - self.scroll) % W), int(cy)), r)
        pygame.draw.rect(c, (178, 112, 70), (0, COUNTER_FRONT_Y, W, 18))
        pygame.draw.rect(c, (205, 140, 92), (0, COUNTER_FRONT_Y, W, 5))
        pygame.draw.rect(c, (140, 86, 52), (0, COUNTER_FRONT_Y + 18, W, H - COUNTER_FRONT_Y - 18))
        x = -int(self.scroll % 320)
        while x < W:
            rounded(c, (156, 98, 60), (x + 18, COUNTER_FRONT_Y + 36, 284, 62), 10, (110, 66, 40), 4)
            pygame.draw.circle(c, (232, 186, 98), (x + 160, COUNTER_FRONT_Y + 67), 8)
            x += 320

    def draw_shadow(self, c, cx, height):
        s = clamp(1.0 - height / 380.0, 0.4, 1.0)
        w, h = int(130 * s), 20
        sh = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (90, 60, 30, 90), (0, 0, w, h))
        c.blit(sh, (int(cx - w / 2), GROUND_Y - 6))

    def draw_dosa_image(self, c, cx, cy, angle):
        img = self.dosa_img
        if abs(angle) > 0.5:
            img = pygame.transform.rotate(img, angle)
        c.blit(img, img.get_rect(center=(int(cx), int(cy))))

    def draw_actors(self, c):
        for o in self.obstacles:
            c.blit(o.surf, (int(o.x), int(o.y)))
        for ch in self.chutneys:
            c.blit(self.halo, self.halo.get_rect(center=(int(ch.x), int(ch.y))))
            c.blit(self.chutney_img, self.chutney_img.get_rect(center=(int(ch.x), int(ch.y))))

        sw, sh = self.dosa_img.get_size()
        st = self.state

        if st in ("menu", "intro", "playing", "paused"):
            angle = 0.0
            bounce = 0.0
            x_off = 0.0
            if st == "menu":
                angle = math.sin(self.run_t * 2.2) * 2
                bounce = math.sin(self.run_t * 3) * 2
            elif st == "intro":
                if INTRO_SCARE_AT <= self.intro_t < INTRO_RUN_AT:
                    x_off = math.sin(self.intro_t * 70) * 3
            elif self.h <= 0.5:
                bounce = -abs(math.sin(self.run_t * 11)) * 7
                angle = math.sin(self.run_t * 11) * 4
            else:
                angle = clamp(self.vy / 90.0, -14, 14)
            cx = DOSA_X + x_off
            cy = GROUND_Y - self.h - sh / 2.0 + bounce
            self.draw_shadow(c, cx, self.h)
            if self.shield_t > 0 and (self.shield_t > 1.5 or int(self.shield_t * 10) % 2 == 0):
                self.draw_shield(c, cx, cy)
            self.draw_dosa_image(c, cx, cy, angle)
            if st == "intro" and INTRO_SCARE_AT <= self.intro_t < INTRO_RUN_AT + 0.1:
                bx, by = int(cx + 20), int(cy - sh / 2.0 - 34)
                rounded(c, (255, 255, 255), (bx - 22, by - 24, 44, 48), 12, (60, 40, 30), 3)
                draw_text(c, "!", self.f_med, (220, 50, 40), (bx, by), shadow=None)

            if self.intro_t < INTRO_END and st in ("intro", "playing", "paused"):
                pose = intro_hand_pose(self.intro_t)
                if pose:
                    hx = pose[0] - (self.scroll if self.intro_t >= INTRO_RUN_AT else 0)
                    draw_hand(c, self.hand_frames, hx, pose[1], pose[2], pose[3])

        elif st == "dying":
            ty = GROUND_Y - self.h - sh * 0.55
            pose = death_hand_pose(self.death_t, (DOSA_X, ty))
            if pose and self.death_t >= 0.8:
                draw_hand(c, self.hand_frames, pose[0], pose[1], pose[2], pose[3])
                self.draw_dosa_image(c, pose[0], pose[1] - 10, 0)
            else:
                self.draw_shadow(c, DOSA_X, self.h)
                self.draw_dosa_image(c, DOSA_X, GROUND_Y - self.h - sh / 2.0, math.sin(self.death_t * 40) * 5)
                if pose:
                    draw_hand(c, self.hand_frames, pose[0], pose[1], pose[2], pose[3])

    def draw_shield(self, c, cx, cy):
        r = int(max(self.dosa_img.get_size()) * 0.78 + math.sin(self.run_t * 8) * 4)
        s = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(s, (120, 255, 150, 70), (r + 4, r + 4), r)
        pygame.draw.circle(s, (60, 220, 110, 200), (r + 4, r + 4), r, 4)
        c.blit(s, (int(cx - r - 4), int(cy - r - 4)))

    def draw_particles(self, c):
        for p in self.particles:
            pygame.draw.circle(c, p["color"], (int(p["x"]), int(p["y"])), p["size"])
        for text, x, y, life, color in self.floaters:
            draw_text(c, text, self.f_small, color, (int(x), int(y)))

    def draw_hud(self, c):
        if self.state not in ("playing", "paused", "dying"):
            return
        draw_panel(c, (18, 16, 360, 108))
        draw_text(c, "SCORE %04d" % (self.final_score if self.state == "dying" else self.score),
                  self.f_med, (255, 223, 150), (36, 22), "topleft")
        c.blit(self.chutney_icon, (36, 72))
        draw_text(c, "x %d" % self.chutney_count, self.f_small, (255, 255, 255), (36 + self.chutney_icon.get_width() + 8, 76), "topleft")
        draw_text(c, "%d m" % self.meters, self.f_small, (200, 235, 210), (220, 76), "topleft")
        draw_panel(c, (W - 250, 16, 232, 56))
        draw_text(c, "BEST %04d" % self.best, self.f_small, (255, 223, 150), (W - 134, 44))
        if self.shield_t > 0 and self.state != "dying":
            draw_panel(c, (18, 134, 360, 44), color=(16, 60, 36))
            draw_text(c, "IMMUNE", self.f_small, (170, 255, 180), (34, 140), "topleft")
            pygame.draw.rect(c, (20, 40, 28), (150, 147, 210, 18), border_radius=9)
            fill = int(210 * self.shield_t / IMMUNITY_MAX)
            if fill > 0:
                pygame.draw.rect(c, (90, 230, 120), (150, 147, fill, 18), border_radius=9)
        if self.state == "playing" and self.play_t < 7:
            draw_text(c, "SPACE / UP / CLICK = JUMP     CATCH CHUTNEY = IMMUNITY (SMASH THROUGH!)",
                      self.f_small, (255, 255, 255), (W // 2, 672))

    def draw_overlays(self, c):
        blink = int(pygame.time.get_ticks() / 450) % 2 == 0
        if self.state == "menu":
            draw_panel(c, (240, 24, 800, 340), outline=(255, 214, 140))
            draw_text(c, "DOSA DASH", self.f_title, (255, 214, 120), (W // 2, 105))
            draw_text(c, "THE GREAT KITCHEN ESCAPE", self.f_small, (245, 245, 225), (W // 2, 180))
            draw_text(c, "A hand is coming for your dosa - RUN!", self.f_small, (255, 255, 255), (W // 2, 232))
            draw_text(c, "SPACE / UP / CLICK = jump      ESC = pause", self.f_tiny, (225, 235, 225), (W // 2, 274))
            if blink:
                draw_text(c, "PRESS ENTER OR CLICK TO START", self.f_med, (255, 190, 90), (W // 2, 328))
        elif self.state == "paused":
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 130))
            c.blit(dim, (0, 0))
            draw_text(c, "PAUSED", self.f_big, (255, 255, 255), (W // 2, H // 2 - 30))
            draw_text(c, "ESC to resume   R to restart", self.f_small, (230, 230, 230), (W // 2, H // 2 + 30))
        elif self.state == "over":
            draw_panel(c, (330, 130, 620, 360), outline=(255, 214, 140))
            draw_text(c, "THE HAND GOT YOU!", self.f_big, (255, 214, 120), (W // 2, 200))
            draw_text(c, "SCORE  %04d" % self.final_score, self.f_med, (255, 255, 255), (W // 2, 282))
            draw_text(c, "%d m   |   %d chutney   |   %d smashed" % (self.meters, self.chutney_count, self.smashed),
                      self.f_tiny, (210, 235, 215), (W // 2, 330))
            draw_text(c, "NEW BEST!" if self.new_best else "BEST  %04d" % self.best, self.f_small,
                      (255, 230, 130), (W // 2, 378))
            if blink:
                draw_text(c, "ENTER / R / CLICK = RUN AGAIN", self.f_small, (255, 190, 90), (W // 2, 438))

    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    Game().run()