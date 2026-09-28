"""The scene's frame: which way is up, where gravity points, units, meter scale and what is in it.

Implements docs/X3D_MAPPINGS.md §1, §4 and §6. Report this before quoting any distance.
"""

import math

import numpy as np

from . import mathx, perspective, relations

Z_UP_FIX = (1.0, 0.0, 0.0, -math.pi / 2)


def _is_z_up_fix(rotation):
    if len(rotation) != 4:
        return False
    return np.allclose(mathx.rotation(rotation), mathx.rotation(Z_UP_FIX), atol=1e-3)


def frame(scene):
    """Frame report: up and gravity, units, extent in meters, body, viewpoints and objects."""
    evidence, warnings = [], list(scene.notes)
    vp = scene.viewpoint()
    up = mathx.normalize(mathx.frame_rotation(vp.parent_matrix) @ [0, 1, 0]) if vp else np.array([0.0, 1.0, 0.0])
    evidence.append("up is +Y of the bound Viewpoint's parent frame (23.3.1)" if vp
                    else "no Viewpoint: default camera at 0 0 10 looking along -Z, +Y up")
    for name, rotation in scene.root_rotations:
        if _is_z_up_fix(rotation):
            evidence.append(f"root Transform {name or ''} rotates Z-up content to Y-up (rotation 1 0 0 -1.5708)")
    for g in scene.physics_gravity:
        if np.linalg.norm(g) > 0 and np.dot(mathx.normalize(g), -up) < 0.99:
            warnings.append(f"RigidBodyCollection.gravity {g} is not along -up")
    if scene.geospatial:
        warnings.append("geospatial nodes present: local up may be the ellipsoid normal, not +Y")

    points = np.concatenate([s.triangles.reshape(-1, 3) for s in scene.shapes]) if scene.shapes else np.zeros((1, 3))
    low, high = points.min(axis=0), points.max(axis=0)
    extent = high - low
    if not any("Z-up" in e for e in evidence) and extent[2] < 0.5 * min(extent[0], extent[1]):
        warnings.append("the scene is flattest along Z: it may be Z-up content without a rotation to Y-up")

    nav = scene.bound_navigation_info(vp)
    objects = []
    for name, shapes in scene.objects().items():
        pts = np.concatenate([s.triangles.reshape(-1, 3) for s in shapes if len(s.triangles)] or [np.zeros((1, 3))])
        objects.append({
            "name": name, "geometry": sorted({s.geometry for s in shapes}),
            "size_m": [round(float(x), 3) for x in pts.max(axis=0) - pts.min(axis=0)],
            "center_m": [round(float(x), 3) for x in (pts.max(axis=0) + pts.min(axis=0)) / 2],
            "structural": relations.is_structural(pts), "rendered": any(s.rendered for s in shapes),
            "movable_by": next((s.mover for s in shapes if s.mover), None),
        })
    viewpoints = []
    for v in scene.viewpoints:
        p = perspective.from_viewpoint(scene, v.name)
        viewpoints.append({"name": v.name, "description": v.description, "authored_eye_m": p.summary()["authored_eye_m"],
                           "eye_m": p.summary()["eye_m"], "falls": p.falls, "forward": p.summary()["forward"]})
    return {
        "file": str(scene.path),
        "units": {"meters_per_unit": scene.unit, "source": scene.unit_source},
        "up": [round(float(x), 4) for x in up], "gravity": [round(float(x), 4) for x in -up], "up_evidence": evidence,
        "extent_m": {"min": [round(float(x), 3) for x in low], "max": [round(float(x), 3) for x in high],
                     "size": [round(float(x), 3) for x in extent]},
        "navigation": {"name": nav.name, "type": nav.type, "walk_gravity": bool(nav.type) and nav.type[0] == "WALK",
                       "avatarSize": nav.avatar_size, "speed": nav.speed, "headlight": nav.headlight,
                       "visibilityLimit": nav.visibility_limit},
        "background_sky": scene.background_sky, "viewpoints": viewpoints, "objects": objects, "warnings": warnings,
    }
