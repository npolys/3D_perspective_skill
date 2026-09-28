"""See a captured screenshot: find where each strongly coloured object landed in the image.

Objects are found by the hue of their Material color, so this works for objects whose color is
saturated enough to stand apart from greys, whites and the Background. It needs Pillow.
"""

import colorsys
import io

import numpy as np

MIN_SATURATION = 0.4        # object colors paler than this cannot be told apart by hue
PIXEL_SATURATION = 0.3
PIXEL_VALUE = 0.12          # shaded faces darker than this are indistinguishable from black
DARK_VALUE = 0.2            # near-black pixels next to an object are taken as its shaded rim
RIM_PX = 8                  # how far that rim may reach from the pixels found by hue
HUE_TOLERANCE_DEG = 20
MIN_PIXELS = 25


def load(png):
    from PIL import Image
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB"), dtype=float) / 255


def _hsv(image):
    r, g, b = image[..., 0], image[..., 1], image[..., 2]
    v = image.max(axis=-1)
    c = v - image.min(axis=-1)
    s = np.where(v > 0, c / np.where(v > 0, v, 1), 0)
    safe = np.where(c > 0, c, 1)
    h = np.where(v == r, ((g - b) / safe) % 6, np.where(v == g, (b - r) / safe + 2, (r - g) / safe + 4)) * 60
    return np.where(c > 0, h, 0), s, v


def _grow_into(mask, allowed, steps):
    """Extend a mask into allowed neighbouring pixels, one pixel per step (4-neighbourhood)."""
    for _ in range(steps):
        grown = mask.copy()
        grown[1:] |= mask[:-1]
        grown[:-1] |= mask[1:]
        grown[:, 1:] |= mask[:, :-1]
        grown[:, :-1] |= mask[:, 1:]
        grown &= allowed | mask
        if (grown == mask).all():
            break
        mask = grown
    return mask


def _box(mask):
    rows, cols = np.nonzero(mask)
    return [int(cols.min()), int(rows.min()), int(cols.max()) + 1, int(rows.max()) + 1]


def object_boxes(png, colors):
    """Where each strongly colored object is in the image, found by the hue of its Material.

    Faces turned away from the lights shade to black, where hue is lost, and black is ambiguous:
    an object's own shaded rim and a neighbour's shadowed face are the same (0, 0, 0). So each
    object gets two boxes, and its true outline lies between them:
      "box":        the pixels that clearly have the object's color;
      "shadow_box": that region extended through touching near-black pixels, up to RIM_PX.
    Objects not found, or too pale to tell apart by hue, get None.
    """
    h, s, v = _hsv(load(png))
    dark = v < DARK_VALUE
    boxes = {}
    for name, rgb in colors.items():
        if rgb is None:
            continue
        th, ts, _ = colorsys.rgb_to_hsv(*rgb)
        if ts < MIN_SATURATION:
            continue
        dh = np.abs(h - th * 360)
        mask = (np.minimum(dh, 360 - dh) < HUE_TOLERANCE_DEG) & (s > PIXEL_SATURATION) & (v > PIXEL_VALUE)
        if mask.sum() < MIN_PIXELS:
            boxes[name] = None
            continue
        boxes[name] = {"box": _box(mask), "shadow_box": _box(_grow_into(mask, dark, RIM_PX))}
    return boxes


def boxes_from_idmap(id_png, id_colors):
    """Extract object bounding boxes deterministically from an id-encoded image.

    id_png: PNG bytes produced by LiveView.capture(include_id_map=True)['id_png']
    id_colors: dict mapping DEF name -> [r,g,b] (0-255 ints) as returned by LiveView

    Returns: dict name -> {"box": [x0,y0,x1,y1]} or None if not present in the image.
    """
    from PIL import Image
    im = Image.open(io.BytesIO(id_png)).convert('RGB')
    arr = np.asarray(im)
    boxes = {}
    # build reverse map color->name using tuples
    rev = {tuple(v): k for k, v in id_colors.items()}
    h, w = arr.shape[:2]
    # for each unique color in the image, find bounding box and assign
    flat = arr.reshape(-1, 3)
    # get unique colors present
    uniq_colors, inverse = np.unique(flat, axis=0, return_inverse=True)
    for i, col in enumerate(map(tuple, uniq_colors)):
        # skip background-like colors (near black) if not mapped
        name = rev.get(col)
        if name is None:
            continue
        mask = inverse.reshape(h, w) == i
        if mask.sum() == 0:
            boxes[name] = None
            continue
        boxes[name] = {"box": _box(mask)}
    # ensure every requested name exists in returned dict
    for n in id_colors.keys():
        boxes.setdefault(n, None)
    return boxes


def agrees(imagined_box, seen, tolerance=3):
    """True when each imagined edge lies between the seen box and its shadow box, within tolerance."""
    for i, edge in enumerate(imagined_box):
        low, high = sorted((seen["box"][i], seen["shadow_box"][i]))
        if not low - tolerance <= edge <= high + tolerance:
            return False
    return True


def within(imagined_box, seen, tolerance=3):
    """True when the clearly colored part lies inside the imagined outline (for partly hidden objects)."""
    b = seen["box"]
    return (b[0] >= imagined_box[0] - tolerance and b[1] >= imagined_box[1] - tolerance
            and b[2] <= imagined_box[2] + tolerance and b[3] <= imagined_box[3] + tolerance)


def background_fraction(png, sky):
    """Share of the image that is the Background sky color."""
    image = load(png)
    return float((np.abs(image - np.asarray(sky)).max(axis=-1) < 0.02).mean())


def presence_fraction_in_box(png, box, background_rgb=None, tolerance=0.02):
    """Estimate fraction of pixels inside box that differ from the background.

    png: PNG bytes
    box: [x0, y0, x1, y1] pixel coordinates
    background_rgb: optional RGB triplet (0-1 floats) to treat as background; if None, estimate
                    background by sampling the four corners of the image.
    tolerance: per-channel difference threshold to consider a pixel non-background.

    Returns float in [0,1] fraction of pixels inside the box judged as foreground.
    """
    image = load(png)
    h, w = image.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    # clamp
    x0 = max(0, min(w, x0)); x1 = max(0, min(w, x1)); y0 = max(0, min(h, y0)); y1 = max(0, min(h, y1))
    if x0 >= x1 or y0 >= y1:
        return 0.0
    crop = image[y0:y1, x0:x1]
    if crop.size == 0:
        return 0.0
    if background_rgb is None:
        # sample 5x5 patches at the four corners and take median color
        def sample_corner(img, cx, cy, size=5):
            H, W = img.shape[:2]
            xs = slice(max(0, cx), min(W, cx + size))
            ys = slice(max(0, cy), min(H, cy + size))
            patch = img[ys, xs]
            if patch.size == 0:
                return np.array([0.0, 0.0, 0.0])
            return np.median(patch.reshape(-1, 3), axis=0)
        corners = [sample_corner(image, 0, 0), sample_corner(image, w - 5, 0),
                   sample_corner(image, 0, h - 5), sample_corner(image, w - 5, h - 5)]
        background_rgb = np.median(np.vstack(corners), axis=0)
    background_rgb = np.asarray(background_rgb, dtype=float)
    diff = np.abs(crop - background_rgb)
    mask = (diff > tolerance).any(axis=-1)
    return float(mask.mean())
