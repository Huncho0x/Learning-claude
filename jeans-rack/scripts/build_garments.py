"""Make the rail pictures from one real product photo of a pair of jeans.

For every pair in app/data.js this cuts the photo out of its background, reshapes the legs
for that pair's fit, re-dyes it to that pair's wash (keeping the gold stitching and copper
rivets), hangs it on a clip hanger, and saves two pictures:

    public/garments/<id>-front.webp   the full front, shown when you hover
    public/garments/<id>-side.webp    the pair seen side-on, as it hangs on the rail

Run it from the jeans-rack folder:

    python3 -m pip install numpy pillow scipy
    python3 scripts/build_garments.py

To use a different photo, replace scripts/source/jeans-photo.png. A front-on shot on a
plain light background works best.
"""

import json
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PHOTO = os.path.join(HERE, "source", "jeans-photo.png")

S = 4  # hanger drawing units -> pixels
W, H = 800, 1230
WAIST_TOP = 176  # where the waistband sits, so the clips bite into it
CLIPS_X = (206, 594)
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)

# How much wider (>1) or narrower (<1) each leg gets from the crotch (p=0) to the hem (p=1).
FITS = {
    "straight": lambda p: 1.0,
    "wide": lambda p: 1 + 0.26 * p,
    "slim": lambda p: 1 - 0.42 * p,
    "baggy": lambda p: 1 + 0.14 * np.minimum(1, p * 2),
    "relaxed": lambda p: 1 + 0.07 * p,
    "flare": lambda p: 0.84 + 0.52 * p**3,
    "barrel": lambda p: 1 + 0.24 * np.sin(np.pi * p) - 0.18 * p,
}


# ---------- colour helpers ----------

def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


def to_lin(c):
    return np.power(np.clip(c, 0, 1), 2.2)


def to_srgb(c):
    return np.power(np.clip(c, 0, 1), 1 / 2.2)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ---------- the photo ----------

def load_cutout():
    """The photo as linear RGB plus an alpha mask with the background removed."""
    src = np.asarray(Image.open(PHOTO).convert("RGB")).astype(np.float32) / 255
    bg_colour = np.median(np.concatenate([src[0], src[-1], src[:, 0], src[:, -1]]), axis=0)
    near_bg = np.abs(src - bg_colour).max(axis=2) < 14 / 255
    labels, _ = ndi.label(near_bg)
    edge_labels = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    bg = np.isin(labels, edge_labels[edge_labels > 0])
    fg = ndi.binary_opening(~bg, iterations=1)
    alpha = ndi.gaussian_filter(ndi.binary_erosion(fg, iterations=1).astype(np.float32), 0.7)
    # edge pixels are mixed with the background; give them the colour of the nearest solid denim
    # so no pale halo shows when the legs are stretched
    _, (iy, ix) = ndi.distance_transform_edt(alpha < 0.98, return_indices=True)
    src = src[iy, ix]
    return to_lin(src), alpha


def place(rgb, alpha):
    """Scale the photo so the waistband lines up with the hanger clips."""
    ys, xs = np.where(alpha > 0.5)
    rows = alpha > 0.5
    band_y = ys.min() + 25  # just below the belt loops
    band = np.where(rows[band_y])[0]
    k = (CLIPS_X[1] - CLIPS_X[0] + 12) / (band[-1] - band[0])
    cx = (band[0] + band[-1]) / 2
    # map every canvas pixel back into the photo
    sy = (YY - WAIST_TOP) / k + band_y - 3
    sx = (XX - W / 2) / k + cx
    out = np.dstack([ndi.map_coordinates(rgb[..., c], [sy, sx], order=1, cval=0) for c in range(3)])
    a = ndi.map_coordinates(alpha, [sy, sx], order=1, cval=0)
    return out, a


def reshape_legs(rgb, alpha, fit):
    """Widen or narrow each leg around its own centre, more towards the hem."""
    f = FITS.get(fit, FITS["straight"])
    solid = alpha > 0.5
    rows = np.where(solid.any(axis=1))[0]
    top, hem = rows.min(), rows.max()
    # crotch: first row (from the top) where the legs separate at the middle
    mid = W // 2
    crotch = next(y for y in range(top + 100, hem) if not solid[y, mid - 3 : mid + 4].any())
    start = crotch - 90  # ease in over the hips
    sx = XX.copy()
    for y in range(start, hem + 1):
        p = np.clip((y - crotch) / (hem - crotch), 0, 1)
        ease = smoothstep(start, crotch + 40, y)
        scale = 1 + (f(p) - 1) * ease
        cols = np.where(solid[y])[0]
        if cols.size == 0:
            continue
        sx[y] = -100  # anything not covered by a reshaped leg below stays empty
        left = cols[cols < mid]
        right = cols[cols >= mid]
        for part, side in ((left, 0), (right, 1)):
            if part.size == 0:
                continue
            a, b = part.min(), part.max()
            if side == 0 and b >= mid - 2:
                b = mid
            if side == 1 and a <= mid + 2:
                a = mid
            c = (a + b) / 2
            half = (b - a) / 2 * scale + 3
            lo, hi = int(max(0, np.floor(c - half))), int(min(W - 1, np.ceil(c + half)))
            span = np.arange(lo, hi + 1)
            # keep the middle seam where it is at the top so the fly doesn't move
            sx[y, span] = c + (span - c) / scale
    rgb = np.dstack([ndi.map_coordinates(rgb[..., c], [YY, sx], order=1, cval=0) for c in range(3)])
    alpha = ndi.map_coordinates(alpha, [YY, sx], order=1, cval=0)
    return rgb, alpha


def dye(rgb, alpha, wash_hex, original):
    """Re-dye the denim to a new wash, keeping the photo's texture and fades."""
    if original:
        return rgb
    target = to_lin(hex_rgb(wash_hex))
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    ref = np.median(lum[alpha > 0.9])
    ratio = lum / (ref + 1e-6)
    brightness = target @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    gamma = 0.7 if brightness > 0.5 else (1.25 if brightness < 0.05 else 1.0)
    dyed = target[None, None, :] * np.power(np.clip(ratio, 0, 4), gamma)[..., None]
    # gold thread, copper rivets and the brass button keep their own colour
    srgb = to_srgb(rgb)
    warm = smoothstep(0.02, 0.12, srgb[..., 0] - srgb[..., 2])
    return dyed * (1 - warm[..., None]) + rgb * warm[..., None]


# ---------- hanger ----------

def line_mask(lines, width_px):
    img = Image.new("L", (W * 2, H * 2), 0)
    d = ImageDraw.Draw(img)
    for pts in lines:
        d.line([(x * 2, y * 2) for x, y in pts], fill=255, width=int(width_px * 2), joint="curve")
    return np.asarray(img.resize((W, H), Image.LANCZOS), dtype=np.float32) / 255


def poly_mask(polys):
    img = Image.new("L", (W * 2, H * 2), 0)
    d = ImageDraw.Draw(img)
    for poly in polys:
        d.polygon([(x * 2, y * 2) for x, y in poly], fill=255)
    return np.asarray(img.resize((W, H), Image.LANCZOS), dtype=np.float32) / 255


def cubic(p0, p1, p2, p3, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return [tuple(p) for p in (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3]


def over(rgb, alpha, layer_rgb, layer_a):
    rgb = rgb * (1 - layer_a[..., None]) + layer_rgb * layer_a[..., None]
    return rgb, np.maximum(alpha, layer_a)


def hook(rgb, alpha, cx):
    pts = [(cx, 104), (cx, 56)] + cubic((cx, 56), (cx, 16), (cx + 48, 8), (cx + 52, 36)) + cubic(
        (cx + 52, 36), (cx + 54, 48), (cx + 44, 56), (cx + 36, 52)
    )
    m = line_mask([pts], 12)
    d = ndi.distance_transform_edt(line_mask([pts], 1) < 0.2)
    t = np.clip(d / 6, 0, 1)
    shade = 0.35 + 0.65 * np.sqrt(1 - t**2) + 0.5 * np.exp(-((t - 0.25) ** 2) / 0.02)
    metal = to_lin(hex_rgb("#d9dbe0"))[None, None, :] * shade[..., None]
    return over(rgb, alpha, metal, m)


def wood(rgb, alpha, poly, rng, y0, y1):
    m = poly_mask([poly])
    v = np.clip((YY - y0) / (y1 - y0), 0, 1)
    cyl = 0.45 + 0.75 * np.sin(np.pi * np.clip(v * 0.9 + 0.05, 0, 1)) - 0.25 * v
    grain = ndi.gaussian_filter(rng.standard_normal((H, W)).astype(np.float32), (0.8, 50))
    grain /= grain.std() + 1e-6
    col = to_lin(hex_rgb("#8a5a37"))[None, None, :] * (1 + 0.12 * grain)[..., None] * cyl[..., None]
    col += (0.18 * np.exp(-(((YY - (y0 + (y1 - y0) * 0.25)) / 4) ** 2)))[..., None]
    return over(rgb, alpha, col, m)


def clip(rgb, alpha, cx, shadow_on=None):
    for x0, x1, y0, y1 in ((cx - 13, cx + 13, 124, 168), (cx - 22, cx + 22, 160, 210)):
        m = poly_mask([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]])
        half = (x1 - x0) / 2
        t = np.clip(np.abs(XX - cx) / half, 0, 1)
        shade = 0.4 + 0.6 * np.sqrt(1 - t**2) - 0.15 * np.clip((YY - 160) / 50, 0, 1)
        shade += 0.6 * np.exp(-(((XX - cx + half * 0.3) / (half * 0.18)) ** 2))
        steel = to_lin(hex_rgb("#c7cace"))[None, None, :] * shade[..., None]
        if shadow_on is not None and y0 == 160:
            sh = ndi.shift(ndi.gaussian_filter(m, 6), (10, 7), order=1) * shadow_on
            rgb = rgb * (1 - 0.45 * sh)[..., None]
        rgb, alpha = over(rgb, alpha, steel, m)
    groove = np.exp(-(((YY - 180) / 1.4) ** 2)) * poly_mask([[(cx - 22, 160), (cx + 22, 160), (cx + 22, 210), (cx - 22, 210)]])
    rgb = rgb * (1 - 0.5 * groove)[..., None]
    return rgb, alpha


def hang_front(rgb, alpha, rng):
    cloth = alpha.copy()
    rgb, alpha = hook(rgb, alpha, W / 2)
    rgb, alpha = wood(rgb, alpha, [(152, 96), (648, 96), (664, 114), (648, 132), (152, 132), (136, 114)], rng, 96, 132)
    for cx in CLIPS_X:
        rgb, alpha = clip(rgb, alpha, cx, shadow_on=cloth)
    return rgb, alpha


def hang_side(rgb, alpha, rng):
    cloth = alpha.copy()
    rgb, alpha = hook(rgb, alpha, W / 2)
    # seen end-on the bar is short and the two clips line up behind each other
    rgb, alpha = wood(rgb, alpha, [(W / 2 - 22, 96), (W / 2 + 22, 96), (W / 2 + 26, 114), (W / 2 + 22, 132), (W / 2 - 22, 132), (W / 2 - 26, 114)], rng, 96, 132)
    rgb, alpha = clip(rgb, alpha, W / 2, shadow_on=cloth)
    return rgb, alpha


# ---------- side view ----------

def side_view(rgb, alpha):
    """The pair as it hangs sideways: one leg's profile, rounded by the light."""
    solid = alpha > 0.5
    mid = W // 2
    out = np.zeros_like(rgb)
    out_a = np.zeros_like(alpha)
    rows = np.where(solid.any(axis=1))[0]
    for y in range(rows.min(), rows.max() + 1):
        cols = np.where(solid[y, :mid + 1])[0]
        if cols.size < 4:
            continue
        breaks = np.where(np.diff(cols) > 1)[0]  # stop at the gap between the legs
        a, b = cols.min(), min(cols[breaks[0]] if breaks.size else cols.max(), mid)
        width = (b - a) * 0.8  # a hanging leg, seen from the side
        lo, hi = mid - width / 2, mid + width / 2
        xs = np.arange(int(np.floor(lo)), int(np.ceil(hi)) + 1)
        u = np.clip((xs - lo) / max(hi - lo, 1), 0, 1)
        src_x = a + u * (b - a)
        out[y, xs] = np.stack([np.interp(src_x, np.arange(W), rgb[y, :, c]) for c in range(3)], axis=1)
        edge = np.clip(np.minimum(xs - lo + 0.5, hi - xs + 0.5), 0, 1)
        out_a[y, xs] = edge * np.interp(src_x, np.arange(W), alpha[y])
        # round it: light from the left, the far side falls into shadow
        shade = 0.38 + 0.72 * np.sin(np.pi * (0.12 + 0.8 * u)) - 0.18 * u
        out[y, xs] *= shade[:, None]
    # the outseam runs down the middle of the side
    seam_x = mid + 2 * np.sin(YY / 90)
    seam = np.exp(-(((XX - seam_x) / 1.6) ** 2)) * (YY > WAIST_TOP + 40)
    out *= (1 - 0.35 * seam)[..., None]
    out += (0.05 * np.exp(-(((XX - seam_x - 3) / 2) ** 2)) * (YY > WAIST_TOP + 40))[..., None] * out_a[..., None]
    return out, out_a


def save(rgb, alpha, path):
    img = np.dstack([to_srgb(rgb), np.clip(alpha, 0, 1)])
    Image.fromarray((img * 255).astype(np.uint8), "RGBA").save(path, "WEBP", quality=86, method=6)


def load_products():
    js = (
        "import('" + os.path.join(ROOT, "app", "data.js").replace("\\", "/") + "')"
        ".then(m => console.log(JSON.stringify(m.PRODUCTS)))"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main():
    out_dir = os.path.join(ROOT, "public", "garments")
    os.makedirs(out_dir, exist_ok=True)
    photo, photo_a = place(*load_cutout())
    for i, p in enumerate(load_products()):
        rng = np.random.default_rng(i)
        rgb, a = reshape_legs(photo, photo_a, p["fit"])
        rgb = dye(rgb, a, p["wash"], p.get("originalWash", False))
        side_rgb, side_a = side_view(rgb, a)
        save(*hang_front(rgb, a, rng), os.path.join(out_dir, f"{p['id']}-front.webp"))
        save(*hang_side(side_rgb, side_a, rng), os.path.join(out_dir, f"{p['id']}-side.webp"))
        print(p["id"])


if __name__ == "__main__":
    main()
