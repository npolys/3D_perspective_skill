"""Check that the imagined view matches what X_ITE and X3DOM actually render, for any scene.

For each Viewpoint and renderer this binds the Viewpoint in the live browser, then compares
- the live camera with the imagined eye (including WALK settling, which differs by renderer), and
- where each strongly coloured object lands in the capture with where it was imagined.

    x3d-perspective verify my_scene.x3d --out-dir captures/

Needs the `live` extra. Objects are found by the hue of their Material color, so objects you want
checked need saturated colors that differ from each other; pale, grey and white objects are skipped.
"""

from pathlib import Path

import numpy as np

from . import imaging, perspective, view, x3d_loader
from .live import RENDERERS, LiveView

TOLERANCE_PX = 3                # silhouette edges shade toward black; allow a few pixels
CAMERA_TOLERANCE_M = 0.01


def object_colors(scene):
    """Object name -> the diffuse (or base) color of its first colored shape."""
    return {name: next((s.diffuse_color for s in shapes if s.diffuse_color), None)
            for name, shapes in scene.objects().items()}


def projected_boxes(imagined, png=None):
    """Project-centred object detection for a captured image.

    This is the simpler, more robust primary path: object locations are taken from the already-
    computed projected pixel_box, and the image is checked for foreground content within that box.
    We still keep the color-based detector as a fallback when an object is too small, too pale or
    difficult to distinguish by hue.
    """
    boxes = {}
    for entry in imagined["objects"]:
        name = entry.get("name")
        box = entry.get("pixel_box")
        if not name or box is None:
            continue
        if png is not None:
            fraction = imaging.presence_fraction_in_box(png, box)
            if fraction <= 0.02:
                continue
        boxes[name] = {"box": list(box), "shadow_box": list(box)}
    return boxes


def compare(imagined, seen, tolerance_px=TOLERANCE_PX):
    """Per-object agreement between an imagined view (view.see) and boxes found in a capture.

    Returns one row per object that can be found by color or geometry projection, with "agrees"
    True or False and a reason.
    """
    rows = []
    for entry in imagined["objects"]:
        name = entry["name"]
        if name not in seen:
            continue
        found = seen[name]
        row = {"name": name, "status": entry.get("status"), "imagined_box": entry.get("pixel_box"),
               "visible_fraction": entry.get("visible_fraction"), "seen": found}
        if entry.get("status") != "VISIBLE":
            row["agrees"] = found is None
            row["reason"] = "" if found is None else f"found in the capture but imagined as {entry.get('status')}"
        elif found is None:
            row["agrees"], row["reason"] = False, "imagined visible but not found in the capture"
        elif entry.get("visible_fraction") == 1.0:
            row["agrees"] = imaging.agrees(entry["pixel_box"], found, tolerance_px)
            row["reason"] = "" if row["agrees"] else "box differs from the imagined box"
        else:
            row["agrees"] = imaging.within(entry["pixel_box"], found, tolerance_px)
            row["reason"] = "" if row["agrees"] else "partly hidden, but seen outside its imagined outline"
        rows.append(row)
    return rows


def check_viewpoint(session, scene, viewpoint=None, size=view.DEFAULT_SIZE, tolerance_px=TOLERANCE_PX,
                    camera_tolerance_m=CAMERA_TOLERANCE_M, png_path=None):
    """Bind one Viewpoint (None: the initially bound one) in a LiveView session and compare."""
    errors_before = len(session.errors)
    if viewpoint is not None:
        session.bind(viewpoint)
    p = perspective.from_viewpoint(scene, viewpoint, renderer=session.renderer)
    camera = session.camera()
    png = session.capture(png_path)
    imagined = view.see(scene, p, size)
    seen = imaging.object_boxes(png, object_colors(scene))
    projected = projected_boxes(imagined, png)
    for name, box in projected.items():
        seen.setdefault(name, box)
    rows = compare(imagined, seen, tolerance_px)
    problems = []
    camera_error = None
    if p.falls:
        problems.append("the viewer falls (WALK with no support); the view shows only the Background")
    else:
        camera_error = float(np.linalg.norm(camera["position"] - p.eye))
        if camera_error > camera_tolerance_m:
            problems.append(f"live camera is {camera_error:.3f} m from the imagined eye")
        if float(np.linalg.norm(camera["forward"] - p.forward)) > 0.01:
            problems.append("live camera looks in a different direction from the imagined view")
    problems += [f"{r['name']}: {r['reason']}" for r in rows if r["agrees"] is False]
    problems += [f"page error: {e}" for e in session.errors[errors_before:]]
    return {
        "viewpoint": p.viewpoint, "renderer": session.renderer, "eye_m": p.summary()["eye_m"],
        "camera_m": [round(float(x), 4) for x in camera["position"]],
        "camera_error_m": None if camera_error is None else round(camera_error, 4),
        "objects": rows, "problems": problems, "ok": not problems,
        "png": str(png_path) if png_path else None,
    }


def verify(scene_path, viewpoints=None, renderers=RENDERERS, size=view.DEFAULT_SIZE, out_dir=None,
           tolerance_px=TOLERANCE_PX, allow_no_sandbox=False):
    """Check every Viewpoint (or the named ones) of a scene in each renderer. Returns a report dict.

    allow_no_sandbox: when True, launch Chromium with --no-sandbox. Default False to avoid running without
    the Chromium sandbox; set True for environments that require it.
    """
    scene = x3d_loader.load(scene_path)
    names = list(viewpoints or [vp.name for vp in scene.viewpoints] or [None])
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
    results = []
    for renderer in renderers:
        with LiveView(scene_path, renderer=renderer, size=size, allow_no_sandbox=allow_no_sandbox) as session:
            for name in names:
                png = Path(out_dir) / f"{renderer}_{name or 'default'}.png" if out_dir else None
                results.append(check_viewpoint(session, scene, name, size, tolerance_px, png_path=png))
    return {"scene": str(scene_path), "size": list(size), "renderers": list(renderers), "viewpoints": names,
            "ok": all(r["ok"] for r in results), "results": results}
