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
