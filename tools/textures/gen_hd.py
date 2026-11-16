"""Look B's higher-detail textures (assets/textures_hd/), made from scratch in code.

Each texture is drawn as a value map (0 = darkest, 1 = brightest) with real detail at the higher size
(blades of grass, pebbles, bark grain, cracks, leaf clusters, board grain), then coloured through a
ramp built from the ORIGINAL 64 px texture's own colours (assets/textures/<same name>), with an
ordered dither between ramp steps. So the colours and the feel stay Miasma's, and the result is still
crisp pixel art, just with four times the pixels.

Run:  python3 tools/textures/gen_hd.py            (writes every texture)
      python3 tools/textures/gen_hd.py dirt planks (only those)
Knobs: SIZE below (256 = 4x the originals), RAMP_STEPS (more = smoother shading, fewer = crunchier).
Everything tiles (all noise wraps round the edges).
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "assets", "textures")
DST = os.path.join(ROOT, "assets", "textures_hd")

SIZE = 256
RAMP_STEPS = 20

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


# --- helpers ----------------------------------------------------------------------------------------

def rng(seed):
    return np.random.default_rng(seed)


def noise(r, scale, size=SIZE):
    """Tileable smooth noise in 0..1: white noise blurred with wrap-round edges."""
    n = ndimage.gaussian_filter(r.random((size, size)), scale, mode="wrap")
    n -= n.min()
    return n / max(n.max(), 1e-6)


def fbm(r, scales=(24, 10, 4, 1.5), weights=(0.5, 0.28, 0.15, 0.07)):
    out = np.zeros((SIZE, SIZE))
    for s, w in zip(scales, weights):
        out += noise(r, s) * w
    out -= out.min()
    return out / out.max()


def stamp(img, y, x, patch, mode="max"):
    """Adds a small patch at (y, x), wrapping round the edges."""
    h, w = patch.shape
    ys = (np.arange(h) + y) % SIZE
    xs = (np.arange(w) + x) % SIZE
    region = img[np.ix_(ys, xs)]
    if mode == "max":
        img[np.ix_(ys, xs)] = np.maximum(region, patch)
    elif mode == "min":
        img[np.ix_(ys, xs)] = np.where(patch < 0, region, np.minimum(region, patch))
    elif mode == "set":
        img[np.ix_(ys, xs)] = np.where(patch < 0, region, patch)
    elif mode == "add":
        img[np.ix_(ys, xs)] = region + patch


def line(img, y0, x0, y1, x1, val, mode="set", width=1):
    n = int(max(abs(y1 - y0), abs(x1 - x0)) * 1.5) + 1
    for t in np.linspace(0, 1, n):
        y = int(round(y0 + (y1 - y0) * t)) % SIZE
        x = int(round(x0 + (x1 - x0) * t)) % SIZE
        for k in range(width):
            xx = (x + k) % SIZE
            if mode == "set":
                img[y, xx] = val
            elif mode == "max":
                img[y, xx] = max(img[y, xx], val)
            else:
                img[y, xx] = min(img[y, xx], val)


def ramp_from(name, steps=RAMP_STEPS):
    """The original texture's colours as a dark-to-light ramp of `steps` shades, evenly spaced in
    brightness from its darkest to its brightest colour (each shade = the average of the original's
    pixels nearest that brightness), so the new texture uses the same colours across the same range."""
    im = np.asarray(Image.open(os.path.join(SRC, name + ".png")).convert("RGB"), dtype=float)
    px = im.reshape(-1, 3)
    lum = px @ np.array([0.299, 0.587, 0.114])
    lo, hi = np.percentile(lum, 0.5), np.percentile(lum, 99.5)
    ramp = []
    for t in np.linspace(lo, hi, steps):
        near = np.argsort(np.abs(lum - t))[:24]
        ramp.append(px[near].mean(axis=0))
    ramp = ndimage.uniform_filter1d(np.array(ramp), 3, axis=0, mode="nearest")
    return np.clip(ramp, 0, 255)


def colourise(value, ramp, dither=1.0, gamma=1.0):
    """Stretches the value map to fill the ramp (2nd..99.5th percentile), then picks shades with an
    ordered dither. gamma > 1 darkens the mid-tones, < 1 lightens them."""
    lo, hi = np.percentile(value, 2), np.percentile(value, 99.5)
    v = np.clip((value - lo) / max(hi - lo, 1e-6), 0, 1) ** gamma * (len(ramp) - 1)
    th = np.tile(BAYER, (SIZE // 4, SIZE // 4)) - 0.5
    idx = np.clip(np.floor(v + 0.5 + th * dither), 0, len(ramp) - 1).astype(int)
    return ramp[idx].astype(np.uint8)


def save(name, rgb):
    os.makedirs(DST, exist_ok=True)
    Image.fromarray(rgb, "RGB").save(os.path.join(DST, name + ".png"))
    print("wrote", name, rgb.shape)


# --- the textures -----------------------------------------------------------------------------------

def forest_grass():
    """Ground grass seen from above: a mat of short blades, dark soil between, a few flowers."""
    r = rng(11)
    v = fbm(r) * 0.35 + 0.18
    clumps = noise(r, 14)
    for _ in range(5200):
        y, x = r.integers(0, SIZE, 2)
        length = r.integers(3, 9)
        lean = r.normal(0, 0.6)
        base = 0.45 + clumps[y, x] * 0.35 + r.random() * 0.15
        for k in range(length):
            t = k / max(length - 1, 1)
            yy = (y - k) % SIZE
            xx = int(round(x + lean * k * 0.5)) % SIZE
            v[yy, xx] = max(v[yy, xx], base + t * 0.22)
    # dark gaps of soil between clumps
    gaps = noise(r, 2.5) < 0.33
    v[gaps & (clumps < 0.55)] *= 0.25
    # tiny pale flowers and seed heads
    for _ in range(60):
        y, x = r.integers(0, SIZE, 2)
        stamp(v, y, x, np.array([[-1, 1.0, -1], [1.0, 0.95, 1.0], [-1, 1.0, -1]]), "set")
    save("forest_grass", colourise(v, ramp_from("forest_grass"), gamma=1.1))


def dirt():
    """The road: packed earth with pebbles, wheel ruts and small cracks."""
    r = rng(21)
    v = fbm(r) * 0.45 + 0.3
    # ruts along the road (the road's texture runs along +V)
    xs = np.arange(SIZE)
    for cx in (70, 186):
        d = np.minimum(np.abs(xs - cx), SIZE - np.abs(xs - cx))
        v -= np.exp(-(d / 9.0) ** 2)[None, :] * 0.12
    for _ in range(420):
        y, x = r.integers(0, SIZE, 2)
        s = r.integers(2, 6)
        yy, xx = np.mgrid[-s:s + 1, -s:s + 1]
        disc = (yy / s) ** 2 + (xx / (s * r.uniform(0.7, 1.3))) ** 2 <= 1
        shade = np.where(disc, 0.62 + 0.25 * (-(yy + xx) / (2 * s)) + r.uniform(-0.1, 0.1), -1)
        stamp(v, y, x, shade, "set")
        # its shadow, down-right
        shadow = np.where(disc, 0.12, -1)
        stamp(v, y + s, x + s // 2 + 1, shadow[: max(1, s // 2)], "min")
    for _ in range(26):
        y, x = r.integers(0, SIZE, 2)
        for _ in range(r.integers(4, 9)):
            ny, nx = y + r.integers(-6, 7), x + r.integers(-6, 7)
            line(v, y, x, ny, nx, 0.1, "min")
            y, x = ny, nx
    save("dirt", colourise(v, ramp_from("dirt")))


def hollow_wood():
    """Bark for the trunks: long wavy grain running up the tree, knots, old moss in the cracks."""
    r = rng(31)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    warp = noise(r, 18) * 26 + noise(r, 6) * 6
    stripes = np.sin((xx + warp) / SIZE * np.pi * 2 * 9)
    v = 0.5 + stripes * 0.22 + fbm(r) * 0.2
    v[stripes < -0.82] = 0.08  # the deep cracks between ridges
    for _ in range(7):
        cy, cx = r.integers(0, SIZE, 2)
        d = np.hypot(((yy - cy + SIZE // 2) % SIZE - SIZE // 2) / 1.8, (xx - cx + SIZE // 2) % SIZE - SIZE // 2)
        ring = np.sin(d * 0.9) * np.exp(-d / 9)
        v += ring * 0.25
        v[d < 3] = 0.1
    v += (noise(r, 0.8) - 0.5) * 0.25
    moss = (noise(r, 4) > 0.72) & (stripes < -0.4)
    v[moss] = 0.78
    save("hollow_wood", colourise(v, ramp_from("hollow_wood")))


def forest_moss():
    """The saplings' leaves: dense clusters of small leaves, lit from above."""
    r = rng(41)
    v = fbm(r) * 0.15
    leaf = []
    for s in (3, 4, 5):
        yy, xx = np.mgrid[-s:s + 1, -s:s + 1]
        shape = (yy / s) ** 2 + (xx / (s * 0.6)) ** 2 <= 1
        leaf.append((shape, yy / s))
    for _ in range(3800):
        y, x = r.integers(0, SIZE, 2)
        shape, ny = leaf[r.integers(0, 3)]
        if r.random() < 0.5:
            shape, ny = shape.T, ny.T
        base = 0.5 + r.random() * 0.3
        stamp(v, y, x, np.where(shape, base - ny * 0.3, -1), "set")
    save("forest_moss", colourise(v, ramp_from("forest_moss"), gamma=1.2))


def forest_rock():
    """Boulders: grey stone broken into plates by cracks, worn edges and patches of pale lichen."""
    r = rng(51)
    v = fbm(r, scales=(30, 12, 5, 2), weights=(0.45, 0.3, 0.17, 0.08)) * 0.6 + 0.2
    # plates: distance to the nearest of a few points (wrapping), cracks where two are nearly as near
    pts = r.random((22, 2)) * SIZE
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(float)
    ds = []
    for py, px in pts:
        dy = np.abs(yy - py); dy = np.minimum(dy, SIZE - dy)
        dx = np.abs(xx - px); dx = np.minimum(dx, SIZE - dx)
        ds.append(np.hypot(dy, dx))
    ds = np.sort(np.array(ds), axis=0)
    gap = ds[1] - ds[0]
    wobble = noise(r, 3) * 3
    v += np.clip(gap / 30.0, 0, 1) * 0.25          # plates bulge a little in the middle
    v[gap + wobble < 2.2] = 0.0                   # the cracks
    v[(gap + wobble >= 2.2) & (gap + wobble < 3.4)] += 0.25   # their lit lips
    lichen = noise(r, 5)
    v[(lichen > 0.76)] = 0.95
    for _ in range(240):
        y, x = r.integers(0, SIZE, 2)
        v[y, x] = 1.0
    save("forest_rock", colourise(v, ramp_from("forest_rock")))


def logs():
    """Logs and palisade stakes: rounded bark ridges running along the log."""
    r = rng(61)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    warp = noise(r, 20) * 10
    ridges = np.sin((xx + warp) / SIZE * np.pi * 2 * 6)
    v = 0.45 + ridges * 0.25 + fbm(r) * 0.25
    grain = noise(r, 1.2)
    v += (grain - 0.5) * 0.2
    v[ridges < -0.9] = 0.05
    save("logs", colourise(v, ramp_from("logs")))


def planks():
    """Boards: four planks with long grain, dark seams and iron nails."""
    r = rng(71)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    board = yy // (SIZE // 4)
    v = np.zeros((SIZE, SIZE))
    for b in range(4):
        rows = board == b
        warp = noise(r, 12) * 14
        grain = np.sin((yy + warp * (b + 1) * 0.4) / 3.0 + b * 1.7) * 0.12
        v[rows] = (0.5 + grain + fbm(r) * 0.2 - 0.1 * (b % 2))[rows]
    seams = (yy % (SIZE // 4)) < 2
    v[seams] = 0.05
    for b in range(4):
        y0 = b * (SIZE // 4) + SIZE // 8
        for x0 in (10, SIZE - 14):
            stamp(v, y0 - 1, x0, np.array([[0.2, 0.2, 0.2], [0.2, 0.92, 0.2], [0.2, 0.2, 0.2]]), "set")
    save("planks", colourise(v, ramp_from("planks")))


def grass_tuft():
    """Look B's grass tufts: a fan of blades on a see-through background (RGBA, alpha cut in game).
    The blades are coloured with forest_grass's ramp, dark at the root, lit at the tips."""
    r = rng(81)
    v = np.zeros((SIZE, SIZE))
    alpha = np.zeros((SIZE, SIZE), bool)
    for _ in range(70):
        x0 = r.uniform(20, SIZE - 20)
        lean = r.normal(0, 0.35)
        h = r.uniform(0.45, 0.95) * SIZE
        w = r.uniform(3, 7)
        for k in range(int(h)):
            t = k / h
            y = SIZE - 1 - k
            x = x0 + lean * k + 18 * lean * t * t
            half = w * (1 - t) ** 0.7 * 0.5 + 0.5
            for xx in range(int(x - half), int(x + half) + 1):
                if 0 <= xx < SIZE and 0 <= y < SIZE:
                    alpha[y, xx] = True
                    v[y, xx] = max(v[y, xx], 0.15 + t * 0.8 + (xx - x) / max(half, 1) * 0.08)
    ramp = ramp_from("forest_grass")
    rgb = colourise(np.where(alpha, v, 0.0), ramp)
    rgba = np.dstack([rgb, np.where(alpha, 255, 0).astype(np.uint8)])
    os.makedirs(DST, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(os.path.join(DST, "grass_tuft.png"))
    print("wrote grass_tuft", rgba.shape)


ALL = {f.__name__: f for f in (forest_grass, dirt, hollow_wood, forest_moss, forest_rock, logs, planks, grass_tuft)}

if __name__ == "__main__":
    names = sys.argv[1:] or list(ALL)
    for n in names:
        ALL[n]()
