"""Object relations and viewer-relative placement, judged from the viewer's perspective.

Implements docs/X3D_MAPPINGS.md §3: "right" is level(view direction) x up, so the same words
name different world directions from different viewpoints.
"""

import dataclasses
import re

import numpy as np

from . import geometry, mathx, view

GEOMETRY_WORDS = {"box": "Box", "cube": "Box", "block": "Box", "sphere": "Sphere", "ball": "Sphere",
                  "cylinder": "Cylinder", "cone": "Cone"}
RELATIONS = ("right of", "left of", "in front of", "behind", "above", "below")
HORIZONTAL = {"right of", "left of", "in front of", "behind"}
OPPOSITE = {"right of": "left of", "behind": "in front of", "above": "below"}
RESTING_GAP_M = 0.03        # an object this close to the surface under it is resting on it


def _points(scene, name):
    shapes = scene.objects().get(name)
    if not shapes:
        raise KeyError(f"no object named {name!r}; have {sorted(scene.objects())}")
    return np.concatenate([s.triangles for s in shapes if len(s.triangles)]).reshape(-1, 3)


def _center(points):
    return (points.min(axis=0) + points.max(axis=0)) / 2


def _reach(points, center, direction):
    """How far the points reach from the center along a direction (support function)."""
    return float(np.max((points - center) @ direction))


def _holds(fp, gp, direction):
    """True when all of the figure lies past all of the ground along the direction."""
    return bool(np.min(fp @ direction) >= np.max(gp @ direction) - 1e-6)


def is_structural(points):
    """Floors, walls and ceilings: thin slabs at least 2.5 m across."""
    size = np.sort(points.max(axis=0) - points.min(axis=0))
    return bool(size[0] < 0.25 and size[2] >= 2.5)


def resolve(scene, p, phrase, size=view.DEFAULT_SIZE):
    """Which object a phrase such as "that box", "the sphere" or "Table" refers to, from this view."""
    words = re.sub(r"\b(that|the|this|a|an)\b", " ", phrase.lower()).split()
    objects = scene.objects()
    by_name = [n for n in objects if n.lower() == " ".join(words)]
    if by_name:
        return {"match": by_name[0], "candidates": by_name, "reason": "DEF name"}
    kind = next((GEOMETRY_WORDS[w] for w in reversed(words) if w in GEOMETRY_WORDS), None)
    if kind is None:
        return {"match": None, "candidates": [], "reason": f"no object name or geometry word in {phrase!r}"}
    candidates = [n for n, shapes in objects.items()
                  if any(s.geometry == kind for s in shapes) and not is_structural(_points(scene, n))]
    visible = []
    if p is not None and len(candidates) > 1:
        seen = {o["name"]: o for o in view.see(scene, p, size)["objects"]}
        visible = [n for n in candidates if seen.get(n, {}).get("status") == "VISIBLE"]
    pool = visible or candidates
    if len(pool) == 1:
        where = "in view" if visible else "in the scene"
        return {"match": pool[0], "candidates": candidates, "reason": f"the only free-standing {kind} {where}"}
    return {"match": None, "candidates": pool, "reason": f"{len(pool)} free-standing {kind} objects; ask which one"}


def relations_between(scene, p, figure, ground, size=view.DEFAULT_SIZE):
    """Which relation words hold for figure versus ground, from this perspective."""
    fp, gp = _points(scene, figure), _points(scene, ground)
    cf, cg = _center(fp), _center(gp)
    directions = p.directions()
    holds, offsets = [], {}
    for word, opposite in OPPOSITE.items():
        d = directions[word]
        offset = float((cf - cg) @ d)
        name, d = (word, d) if offset >= 0 else (opposite, -d)
        offsets[name] = round(abs(offset), 3)
        if _holds(fp, gp, d):
            holds.append(name)
    uv, _ = view.project(p, np.stack([cf, cg]), *size)
    return {"figure": figure, "ground": ground, "viewpoint": p.viewpoint, "relations": holds,
            "center_offsets_m": offsets,
            "image_u": {"figure": round(float(uv[0, 0]), 1), "ground": round(float(uv[1, 0]), 1)}}


def _gap_below(scene, point, down, exclude):
    """Distance from a point down to the nearest collidable surface, and what that surface is."""
    triangles, owners, _ = scene.triangles(collidable=True, exclude=exclude)
    t, index = geometry.raycast(point[None], down[None], triangles)
    return (float(t[0]), owners[index[0]]) if index[0] >= 0 else (None, None)


def place(scene, p, figure, relation, ground, gap=0.1, size=view.DEFAULT_SIZE):
    """Where to move figure so it is `relation` ground from this perspective, as an X3D field change."""
    if relation not in RELATIONS:
        raise ValueError(f"relation must be one of {RELATIONS}")
    d, up = p.directions()[relation], p.up
    fp, gp = _points(scene, figure), _points(scene, ground)
    cf, cg = _center(fp), _center(gp)
    target = cg + d * (_reach(gp, cg, d) + _reach(fp, cf, -d) + gap)
    notes = []
    if relation in HORIZONTAL:
        # Keep the figure's height, and if it rests on something, rest it on whatever is under the new spot.
        target += up * float((cf - target) @ up)
        bottom = cf + up * float(np.min((fp - cf) @ up))
        old_gap, old_support = _gap_below(scene, bottom + up * 0.01, -up, {figure})
        if old_gap is not None and old_gap - 0.01 < RESTING_GAP_M:
            new_gap, new_support = _gap_below(scene, bottom + (target - cf) + up * 0.01, -up, {figure})
            if new_gap is None:
                notes.append("nothing under the new spot: it would float")
            else:
                target -= up * (new_gap - old_gap)
                notes.append(f"rests on {new_support}, as it rested on {old_support}")
    shapes = scene.objects()[figure]
    mover = next((s for s in shapes if s.mover), None)
    if mover is None:
        raise ValueError(f"{figure} has no DEF'd Transform above it to move; wrap it in <Transform DEF=...>")
    delta = target - cf
    translation = mover.mover_translation + np.linalg.solve(mover.mover_parent_matrix[:3, :3], delta / scene.unit)
    moved = fp + delta
    overlaps = [name for name in scene.objects() if name != figure and _boxes_overlap(moved, _points(scene, name))]
    after = {o["name"]: o for o in view.see(moved_scene(scene, figure, delta), p, size)["objects"]}
    return {
        "figure": figure, "relation": relation, "ground": ground, "viewpoint": p.viewpoint,
        "direction_world": [round(float(x), 4) for x in d],
        "set_field": {"def": mover.mover, "field": "translation", "value": " ".join(f"{x:.4g}" for x in translation)},
        "new_center_m": [round(float(x), 4) for x in target],
        "imagined_after": {name: {k: after[name].get(k) for k in ("status", "pixel_box", "center_px", "visible_fraction")}
                           for name in (figure, ground)},
        "relation_holds": _holds(moved, gp, d), "overlaps": overlaps, "notes": notes,
    }


def moved_scene(scene, name, delta):
    """A copy of the scene with one object's shapes moved by delta (meters)."""
    copy = dataclasses.replace(scene)
    copy.shapes = [dataclasses.replace(s, triangles=s.triangles + delta) if s.object == name else s for s in scene.shapes]
    return copy


def with_translation(scene, def_name, value):
    """A copy of the scene with a DEF'd Transform's translation set, or None if nothing moves with it.

    Covers shapes whose nearest DEF'd Transform is def_name.
    """
    shapes = [s for s in scene.shapes if s.mover == def_name]
    if not shapes:
        return None
    new = np.array(mathx.floats(value))
    delta = shapes[0].mover_parent_matrix[:3, :3] @ (new - shapes[0].mover_translation) * scene.unit
    copy = dataclasses.replace(scene)
    copy.shapes = [dataclasses.replace(s, triangles=s.triangles + delta, mover_translation=new) if s.mover == def_name
                   else s for s in scene.shapes]
    return copy


def _boxes_overlap(a, b):
    return bool(np.all(a.min(axis=0) < b.max(axis=0) - 1e-3) and np.all(a.max(axis=0) > b.min(axis=0) + 1e-3))
