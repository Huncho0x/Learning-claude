"""Render a photo-style image of every pair on the rail.

Builds each garment from the same shapes as app/components/Jeans.js, then simulates the
cloth: woven twill, uneven yarn, wash fades, whiskers, hanging folds, raised seams,
topstitching and metal hardware, all lit from the top left.

Run it from the jeans-rack folder after changing a pair in app/data.js:

    python3 -m pip install numpy pillow scipy
    python3 scripts/render_garments.py

Images are written to public/garments/<id>.webp.
"""

import json
import os
import subprocess
import zlib

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

S = 4  # pixels per drawing unit (the drawing is 200 x 380 units)
W, H = 200 * S, 380 * S
SS = 2  # supersampling for smooth edges
HEM_Y = 372
CROTCH = (100, 150)

FITS = {
    "straight": dict(ox=36, w=54, c1=(40, 150), c2=(36, 260)),
    "wide": dict(ox=16, w=78, c1=(38, 150), c2=(18, 260)),
    "slim": dict(ox=52, w=38, c1=(38, 140), c2=(50, 250)),
    "baggy": dict(ox=22, w=72, c1=(26, 160), c2=(20, 280)),
    "carpenter": dict(ox=30, w=62, c1=(34, 150), c2=(30, 270)),
    "flare": dict(ox=18, w=76, c1=(42, 170), c2=(56, 270)),
    "cargo": dict(ox=28, w=62, c1=(30, 160), c2=(26, 280)),
    "pleated": dict(ox=32, w=58, c1=(36, 150), c2=(32, 270)),
    "barrel": dict(ox=46, w=46, c1=(18, 190), c2=(26, 310)),
}

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)


# ---------- small helpers ----------

def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


def to_lin(c):
    return np.power(c, 2.2)


def to_srgb(c):
    return np.power(np.clip(c, 0, 1), 1 / 2.2)


def cubic(p0, p1, p2, p3, n=60):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    pts = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3
    return [tuple(p) for p in pts]


def quad(p0, p1, p2, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = map(np.array, (p0, p1, p2))
    pts = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t**2 * p2
    return [tuple(p) for p in pts]


def mirror(pts):
    return [(200 - x, y) for x, y in pts]


def shift(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def polygon_mask(polys):
    img = Image.new("L", (W * SS, H * SS), 0)
    d = ImageDraw.Draw(img)
    for poly in polys:
        d.polygon([(x * S * SS, y * S * SS) for x, y in poly], fill=255)
    img = img.resize((W, H), Image.LANCZOS)
    return np.asarray(img, dtype=np.float32) / 255


def line_mask(lines, width_units, dash=None):
    """Antialiased mask of polylines. dash=(on, off) in units gives stitching."""
    img = Image.new("L", (W * SS, H * SS), 0)
    d = ImageDraw.Draw(img)
    wpx = max(1, int(round(width_units * S * SS)))
    for pts in lines:
        pts = [(x * S * SS, y * S * SS) for x, y in pts]
        if not dash:
            d.line(pts, fill=255, width=wpx, joint="curve")
            continue
        on, off = dash[0] * S * SS, dash[1] * S * SS
        pos, drawing, left = 0.0, True, on
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            seg = np.hypot(x1 - x0, y1 - y0)
            t = 0.0
            while t < seg:
                step = min(left, seg - t)
                if drawing:
                    a, b = t / seg, (t + step) / seg
                    d.line(
                        [(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)],
                        fill=255,
                        width=wpx,
                    )
                t += step
                left -= step
                if left <= 1e-6:
                    drawing = not drawing
                    left = on if drawing else off
    img = img.resize((W, H), Image.LANCZOS)
    return np.asarray(img, dtype=np.float32) / 255


def dist_to(lines):
    """Distance in pixels from every pixel to the nearest of these polylines."""
    m = line_mask(lines, 0.3) > 0.2
    return ndi.distance_transform_edt(~m).astype(np.float32)


def noise(rng, sigma, amp=1.0):
    n = ndi.gaussian_filter(rng.standard_normal((H, W)).astype(np.float32), sigma, mode="wrap")
    return n / (n.std() + 1e-6) * amp


def ridge(d, width, height=1.0):
    return height * np.exp(-((d / width) ** 2))


def normalize(v):
    return v / (np.abs(v).max() + 1e-6)


# ---------- garment geometry ----------

def leg_outline(fit):
    f = FITS.get(fit, FITS["straight"])
    ox, w, c1, c2 = f["ox"], f["w"], f["c1"], f["c2"]
    ix = ox + w
    outer = cubic((42, 64), c1, c2, (ox, HEM_Y))
    inner = cubic((ix, HEM_Y + 2), (ix + 2, 290), (CROTCH[0] - 3, 200), CROTCH)
    poly = [(CROTCH[0], 44), (42, 44)] + outer + inner
    return poly, outer, inner, ox + w / 2


def build(product):
    fit, kind, pid = product["fit"], product["kind"], product["id"]
    denim = kind == "jeans"
    rng = np.random.default_rng(zlib.crc32(pid.encode()))

    left, outer, inner, hem_mid = leg_outline(fit)
    right = mirror(left)
    body = polygon_mask([left, right])
    loops_x = [52, 80, 120, 148]
    loops = polygon_mask([[(x - 3, 42), (x + 3, 42), (x + 3, 62), (x - 3, 62)] for x in loops_x])
    cloth = np.maximum(body, loops)
    inside = body > 0.5
    edge_d = ndi.distance_transform_edt(inside).astype(np.float32)  # px from the silhouette edge
    u_y = YY / S  # drawing units, for placing things vertically

    # ---- height map: how far each point of cloth sticks out towards you ----
    hmap = np.zeros((H, W), np.float32)
    # round legs
    hmap += 10 * np.sqrt(np.clip(edge_d, 0, 60) / 60)
    # the weight of the legs pulls long vertical folds down from the clips
    drape_amp = {"wide": 1.6, "baggy": 1.5, "flare": 1.2, "cargo": 1.3, "pleated": 1.1}.get(fit, 0.9)
    for _ in range(5):
        lam = rng.uniform(30, 60) * S
        phase = rng.uniform(0, 2 * np.pi)
        wobble = rng.uniform(4, 10) * S * np.sin(YY / (rng.uniform(60, 120) * S) + rng.uniform(0, 6))
        env = np.clip((u_y - 60) / 50, 0, 1) * rng.uniform(0.6, 1.4)
        hmap += drape_amp * 7.0 * env * np.sin(2 * np.pi * (XX + wobble) / lam + phase)
    # tight folds fanning out under each clip
    for cx in (51.5, 148.5):
        dx = (XX / S - cx) / np.clip((u_y - 44) * 0.35 + 3, 3, 30)
        fan = np.exp(-np.clip(u_y - 48, 0, None) / 45) * (u_y > 48)
        hmap += 2.4 * fan * np.cos(dx * 2.6) * np.exp(-(dx**2) / 6)
    # soft creases behind the knee and where the hem stacks
    for ky, amp in ((245, 1.4), (340, 1.0 if fit in ("wide", "baggy", "flare") else 0.5)):
        yk = ky + 6 * np.sin(XX / (17 * S) + rng.uniform(0, 6))
        hmap += amp * 2 * np.exp(-(((u_y - yk) * S / (7 * S)) ** 2)) * np.sin(XX / (9 * S) + rng.uniform(0, 6))
    hmap += noise(rng, 18, 0.6)  # small ripples

    # waistband and seams stand proud of the leg
    band = (u_y >= 44) & (u_y <= 60)
    hmap += np.where(band, 3.0, 0.0)
    hmap -= ridge(np.abs(u_y - 60) * S, 1.6, 2.2)  # waistband seam groove
    lower = u_y > 66
    hmap += lower * ridge(edge_d - 5, 2.2, 1.6)  # outseam / inseam ridge
    hmap -= lower * ridge(edge_d - 8, 1.5, 0.8)
    # fly placket
    fly = [(100, 60), (100, 128)]
    jstitch = [(112, 60), (112, 118 if denim else 112)] + quad(
        (112, 118 if denim else 112), (112, 130 if denim else 124), (100, 134 if denim else 128)
    )
    hmap -= ridge(dist_to([fly]), 1.6, 3.0)
    hmap += ridge(dist_to([shift(fly, 1.2, 0)]), 2.0, 1.2)
    # front pockets: the opening is a folded edge, the pocket bag sits a little deeper
    pocket_l = quad((74, 60), (72, 94), (40, 102))
    pocket_r = mirror(pocket_l)
    bag = polygon_mask([pocket_l + [(38, 102), (38, 60)], pocket_r + [(162, 102), (162, 60)]])
    hmap -= bag * 2.5
    d_pk = dist_to([pocket_l, pocket_r])
    hmap += ridge(d_pk, 2.5, 1.8)
    coin = [(132, 64), (148, 64), (149, 80), (140, 83), (131, 80), (132, 64)]
    if denim:
        hmap += polygon_mask([coin]) * 1.2
        hmap -= ridge(dist_to([coin]), 1.2, 0.8)
    # loops
    hmap += loops * 5
    # extras
    creases = []
    if fit in ("pleated", "slim"):
        creases = [[(70, 60), (hem_mid, HEM_Y)], [(130, 60), (200 - hem_mid, HEM_Y)]]
        hmap += ridge(dist_to(creases), 1.8 if fit == "pleated" else 3, 3.5 if fit == "pleated" else 1.5)
    pleats = []
    if fit == "pleated":
        pleats = [[(80, 60), (81, 98)], [(88, 60), (88, 86)], [(120, 60), (119, 98)], [(112, 60), (112, 86)]]
        hmap -= ridge(dist_to(pleats), 1.5, 2.2)
        hmap += ridge(dist_to([shift(p, 1.2, 0) for p in pleats]), 1.8, 1.2)
    patches = []  # (polygon, raise)
    if fit == "cargo":
        for side in (0, 1):
            box = [(30, 198), (72, 198), (72, 254), (30, 254), (30, 198)]
            flap = [(28, 192), (74, 192), (74, 208), (28, 208), (28, 192)]
            if side:
                box, flap = mirror(box), mirror(flap)
            patches += [(box, 2.5), (flap, 4.0)]
    if fit == "carpenter":
        patches += [([(140, 112), (162, 112), (162, 196), (140, 196), (140, 112)], 2.0)]
        patches += [([(30, 170), (46, 170), (46, 180), (30, 180), (30, 170)], 3.5)]
    for poly, rise in patches:
        m = polygon_mask([poly])
        hmap += ndi.gaussian_filter(m, 1.5) * rise
        hmap -= ridge(dist_to([poly]), 1.2, 1.0)
    # hem: a thick folded band with a rolled edge
    hem_band = (u_y > HEM_Y - 10) & (u_y < HEM_Y + 3)
    hmap += hem_band * 2.2
    hmap -= ridge(np.abs(u_y - (HEM_Y - 10)) * S, 1.5, 1.8)

    hmap = ndi.gaussian_filter(hmap, 0.8)

    # ---- lighting ----
    gy, gx = np.gradient(hmap)
    n = np.dstack([-gx * 1.5, -gy * 1.5, np.ones_like(hmap)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    light = np.array([-0.45, -0.55, 0.7], np.float32)
    light /= np.linalg.norm(light)
    diffuse = np.clip((n * light).sum(axis=2), 0, 1)
    ao = np.clip(1 - 0.06 * np.clip(ndi.gaussian_filter(hmap, 10) - hmap, 0, None), 0.45, 1)
    rim = 0.72 + 0.28 * np.clip(edge_d / 18, 0, 1)
    shade = (0.22 + 0.95 * diffuse) * ao * rim * (1 - 0.12 * np.clip((u_y - 60) / 310, 0, 1))
    # clips cast a small shadow on the waistband
    clip_shadow = polygon_mask([[(46, 40), (57, 40), (57, 53), (46, 53)], [(143, 40), (154, 40), (154, 53), (143, 53)]])
    shade *= 1 - 0.45 * ndi.shift(ndi.gaussian_filter(clip_shadow, 5), (8, 6), order=1)

    # ---- the cloth itself ----
    wash = to_lin(hex_rgb(product["wash"]))
    fade = np.zeros((H, W), np.float32)
    if denim:
        is_dark = product["wash"].lower() in ("#22335a", "#2a2a2e")
        k = 0.45 if is_dark else 1.0
        # thighs and seat wear lighter
        for cx in (68, 132):
            fade += k * 0.38 * np.exp(-(((XX / S - cx) / 26) ** 2) - ((u_y - 175) / 70) ** 2)
        fade += k * 0.2 * np.exp(-(((u_y - 300) / 45) ** 2))
        # whiskers fanning out from the crotch
        wh = []
        for side in (-1, 1):
            for i in range(3):
                y0 = 134 + i * 7 + rng.uniform(-2, 2)
                length = 24 - i * 3 + rng.uniform(-4, 4)
                x0 = 100 + side * (5 + i)
                wh.append(quad((x0, y0), (x0 + side * length * 0.5, y0 - 2), (x0 + side * length, y0 + 4 + i)))
        whisk = ndi.gaussian_filter(line_mask(wh, 1.6), 4.5)
        fade += k * 0.9 * whisk
        # raised places rub pale: fold crests, seams, pocket edges, hem
        crest = np.clip(ndi.gaussian_filter(hmap, 2) - ndi.gaussian_filter(hmap, 12), 0, None)
        fade += k * 0.22 * crest
        fade += k * 0.6 * ridge(d_pk - 3, 4)
        fade += k * 0.4 * lower * ridge(edge_d - 4, 5)
        rope = 0.5 + 0.5 * np.sin((XX + YY * 0.7) / (3.2 * S))
        fade += k * hem_band * (0.4 + 0.5 * rope)
        fade += k * band * 0.2
        fade *= 1 + noise(rng, 14, 0.18)
        fade = np.clip(fade, 0, 1.3)

    # weave
    if fit in ("cargo",):
        # cotton ripstop: plain weave with a reinforcing grid
        grid = ((XX % (5 * S)) < 0.8 * S) | ((YY % (5 * S)) < 0.8 * S)
        tex = 1 + 0.05 * np.sin(XX * 2.2) * np.sin(YY * 2.2) + 0.06 * grid + noise(rng, 0.8, 0.04) + noise(rng, (30, 3), 0.03)
        color = wash[None, None, :] * tex[..., None]
    elif fit == "pleated":
        # wool: heathered fibres with a faint sheen
        fib = noise(rng, 0.6, 1.0)
        tex = 1 + 0.10 * fib + noise(rng, 3, 0.04)
        color = wash[None, None, :] * tex[..., None]
        color += (0.04 * np.clip(fib, 0, None))[..., None] * np.array([1, 1, 1], np.float32)
    else:
        # denim: indigo warp over white weft, 3x1 right-hand twill
        period = 1.15 * S
        twill = 0.5 + 0.5 * np.sin(2 * np.pi * (XX * 0.94 - YY * 0.34) / period)
        warp_thread = 0.5 + 0.5 * np.sin(2 * np.pi * XX / (0.6 * S))
        slub = noise(rng, (140, 0.7), 1.0)  # uneven yarn gives the vertical streaks
        weft_show = 0.06 + 0.12 * (1 - twill) * (0.6 + 0.4 * warp_thread) + 0.03 * np.clip(slub, 0, None)
        weft = to_lin(hex_rgb("#e8e4da"))
        if product["wash"].lower() == "#2a2a2e":
            weft = to_lin(hex_rgb("#8c8c90"))
        dark = wash * 0.75
        pale = to_lin(np.clip(hex_rgb(product["wash"]) * 0.7 + np.array([0.26, 0.29, 0.33]), 0, 1))
        if product["wash"].lower() == "#e6dcc6":  # ecru: undyed, pale flecks
            dark = wash * 0.92
            pale = wash * 1.05
            weft = to_lin(hex_rgb("#f4efe3"))
        f3 = np.clip(fade, 0, 1)[..., None]
        yarn = dark[None, None, :] * (1 - f3) + pale[None, None, :] * f3
        yarn = yarn * (1 + 0.06 * slub[..., None] + noise(rng, 5, 0.04)[..., None] + noise(rng, 0.7, 0.05)[..., None])
        w3 = np.clip(weft_show + 0.35 * np.clip(fade, 0, 1) * (1 - twill) * 0.6, 0, 1)[..., None]
        color = yarn * (1 - w3) + weft[None, None, :] * w3
        if product["wash"].lower() == "#e6dcc6":
            specks = (noise(rng, 0.7, 1.0) > 3.1).astype(np.float32)
            color *= (1 - 0.35 * specks)[..., None]

    rgb = color * shade[..., None]

    # ---- topstitching ----
    thread = to_lin(hex_rgb(product["stitch"]))
    st = []
    st += [[(0, 46.8), (200, 46.8)], [(0, 57.4), (200, 57.4)]]
    st += [jstitch, shift(jstitch, 2.0, 0) if denim else []]
    st += [pocket_l, shift(pocket_l, 1.4, 1.6), pocket_r, shift(pocket_r, -1.4, 1.6)]
    if denim:
        st += [[(132, 66.2), (148, 66.2)], [(132, 68), (148, 68)]]
        st += [[(0, HEM_Y - 8.2), (200, HEM_Y - 8.2)], [(0, HEM_Y - 6.4), (200, HEM_Y - 6.4)]]
    else:
        st += [[(0, HEM_Y - 8.2), (200, HEM_Y - 8.2)]]
    for poly, _ in patches:
        st.append(shift(poly, 0, 0))
    st = [s for s in st if s]
    smask = line_mask(st, 0.55, dash=(1.1, 0.55)) * (body > 0.5)
    sshadow = ndi.shift(ndi.gaussian_filter(smask, 0.9), (1.2, 0.8), order=1)
    rgb *= (1 - 0.45 * sshadow)[..., None]
    thread_rgb = thread[None, None, :] * (0.55 + 0.75 * diffuse)[..., None]
    rgb = rgb * (1 - smask[..., None]) + thread_rgb * smask[..., None]

    # ---- metal: rivets and the waist button ----
    alpha = cloth.copy()
    hardware = []
    if denim:
        hardware += [((74, 61.5), 1.7, "#b8733d"), ((126, 61.5), 1.7, "#b8733d"), ((41.5, 101), 1.6, "#b8733d"), ((158.5, 101), 1.6, "#b8733d")]
        hardware += [((110, 52), 4.4, "#c9c6bd")]
    else:
        hardware += [((110, 52), 3.6, "#2a2a2a")]
    for (cx, cy), r, col in hardware:
        d = np.hypot(XX / S - cx, YY / S - cy)
        m = np.clip((r - d) * S * 0.9, 0, 1)
        dx, dy = (XX / S - cx) / r, (YY / S - cy) / r
        dome = np.clip(1 - dx**2 - dy**2, 0, 1)
        spec = np.exp(-(((dx + 0.35) ** 2 + (dy + 0.4) ** 2) / 0.08))
        ring = np.exp(-(((d - r * 0.62) / (0.12 * r)) ** 2))
        base = to_lin(hex_rgb(col))
        metal = base[None, None, :] * (0.45 + 0.6 * dome)[..., None] * (1 - 0.35 * ring)[..., None] + spec[..., None] * 0.9
        sh = ndi.shift(ndi.gaussian_filter(m, 2), (3, 2), order=1)
        rgb *= (1 - 0.4 * sh)[..., None]
        rgb = rgb * (1 - m[..., None]) + metal * m[..., None]

    # ---- let the cloth hang: bend everything below the waistband a little ----
    env = np.clip((u_y - 62) / 120, 0, 1)
    dx = np.zeros((H, W), np.float32)
    for _ in range(3):
        dx += rng.uniform(0.6, 1.3) * S * np.sin(YY / (rng.uniform(40, 90) * S) + rng.uniform(0, 6))
    dx *= env
    coords = [YY, XX - dx]
    rgb = np.dstack([ndi.map_coordinates(rgb[..., c], coords, order=1, mode="nearest") for c in range(3)])
    alpha = ndi.map_coordinates(alpha, coords, order=1, mode="constant", cval=0)

    # ---- the hanger ----
    rgb, alpha = draw_hanger(rgb, alpha, rng)

    out = np.dstack([to_srgb(rgb), np.clip(alpha, 0, 1)])
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")


def metal_tube(rgb, alpha, lines, radius, base="#d9dbe0"):
    d = dist_to(lines)
    r = radius * S
    m = np.clip(r - d + 0.5, 0, 1)
    t = np.clip(d / r, 0, 1)
    col = to_lin(hex_rgb(base))
    prof = 0.35 + 0.65 * np.sqrt(1 - t**2)
    spec = np.exp(-((t - 0.25) ** 2) / 0.02)
    metal = col[None, None, :] * prof[..., None] + 0.5 * spec[..., None]
    rgb = rgb * (1 - m[..., None]) + metal * m[..., None]
    return rgb, np.maximum(alpha, m)


def draw_hanger(rgb, alpha, rng):
    # hook
    hook = [(100, 26), (100, 14)] + cubic((100, 14), (100, 4), (112, 2), (113, 9)) + cubic((113, 9), (113.5, 12), (111, 14), (109, 13))
    rgb, alpha = metal_tube(rgb, alpha, [hook], 1.6)
    # wooden bar with grain
    bar = polygon_mask([[(38, 24), (162, 24), (166, 28.5), (162, 33), (38, 33), (34, 28.5)]])
    v = np.clip((YY / S - 24) / 9, 0, 1)
    cyl = 0.45 + 0.75 * np.sin(np.pi * np.clip(v * 0.9 + 0.05, 0, 1)) - 0.25 * v
    grain = noise(rng, (0.8, 60), 1.0)
    rings = 0.5 + 0.5 * np.sin(YY / (0.9 * S) + 3 * noise(rng, (4, 80), 1.0))
    wood = to_lin(hex_rgb("#8a5a37"))[None, None, :] * (1 + 0.12 * grain + 0.12 * rings)[..., None] * cyl[..., None]
    spec = np.exp(-(((YY / S - 26.2) / 1.0) ** 2)) * 0.18
    wood = wood + spec[..., None]
    rgb = rgb * (1 - bar[..., None]) + wood * bar[..., None]
    alpha = np.maximum(alpha, bar)
    # clips: arms down from the bar and jaws biting the waistband
    for cx in (51.5, 148.5):
        arm = polygon_mask([[(cx - 3.2, 31), (cx + 3.2, 31), (cx + 3.2, 42), (cx - 3.2, 42)]])
        jaw = polygon_mask([[(cx - 5.5, 40), (cx + 5.5, 40), (cx + 5.5, 52.5), (cx - 5.5, 52.5)]])
        for part, half in ((arm, 3.2), (jaw, 5.5)):
            t = np.clip(np.abs(XX / S - cx) / half, 0, 1)
            prof = 0.4 + 0.6 * np.sqrt(1 - t**2) - 0.15 * np.clip((YY / S - 40) / 12, 0, 1)
            spec = np.exp(-(((XX / S - cx + half * 0.3) / (half * 0.18)) ** 2)) * 0.6
            steel = to_lin(hex_rgb("#c7cace"))[None, None, :] * prof[..., None] + spec[..., None]
            rgb = rgb * (1 - part[..., None]) + steel * part[..., None]
            alpha = np.maximum(alpha, part)
        # the spring line across the jaw
        groove = np.exp(-(((YY / S - 45) / 0.35) ** 2)) * jaw
        rgb *= (1 - 0.5 * groove)[..., None]
    return rgb, alpha


def load_products():
    """Read PRODUCTS out of app/data.js with node so this script never drifts from the site."""
    js = (
        "import('" + os.path.join(ROOT, "app", "data.js").replace("\\", "/") + "')"
        ".then(m => console.log(JSON.stringify(m.PRODUCTS)))"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main():
    out_dir = os.path.join(ROOT, "public", "garments")
    os.makedirs(out_dir, exist_ok=True)
    for p in load_products():
        img = build(p)
        path = os.path.join(out_dir, f"{p['id']}.webp")
        img.save(path, "WEBP", quality=88, method=6)
        print(f"{path}  {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    main()
