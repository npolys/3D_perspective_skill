"""Imagine the 2D view: where each object lands in the frame, how big, and whether it is visible.

Implements docs/X3D_MAPPINGS.md §2 (projection) and §7 (visibility reason codes).
"""

import math

import numpy as np

from . import geometry

DEFAULT_SIZE = (1280, 720)
OPAQUE_BELOW = 0.5          # transparency under this blocks the line of sight
MAX_SAMPLES = 300


def focal_px(p, width, height):
    """Focal length in pixels: fieldOfView spans the smaller side of the view (23.3.1)."""
    return (min(width, height) / 2) / math.tan(p.field_of_view / 2)


def to_camera(p, points):
    """Camera coordinates: x right, y up, z depth in front of the eye."""
    d = np.asarray(points, dtype=float) - p.eye
    return np.stack([d @ p.right, d @ p.camera_up, d @ p.forward], axis=-1)


def _pixels(p, camera_points, width, height):
    c = np.asarray(camera_points, dtype=float).reshape(-1, 3)
    if p.kind == "OrthoViewpoint":
        min_x, min_y, max_x, max_y = (list(p.field_of_view) + [-1, -1, 1, 1][len(p.field_of_view):])[:4]
        k = min(width / (max_x - min_x), height / (max_y - min_y))
        return np.stack([width / 2 + (c[:, 0] - (min_x + max_x) / 2) * k,
                         height / 2 - (c[:, 1] - (min_y + max_y) / 2) * k], axis=1)
    f = focal_px(p, width, height)
    z = np.where(np.abs(c[:, 2]) < 1e-12, 1e-12, c[:, 2])
    return np.stack([width / 2 + f * c[:, 0] / z, height / 2 - f * c[:, 1] / z], axis=1)


def project(p, points, width, height):
    """Pixel (u, v) and depth of world points; only meaningful for points in front of the eye."""
    c = to_camera(p, points)
    return _pixels(p, c, width, height), c[:, 2]


def _clip(polygon, inside, cross):
    """Sutherland-Hodgman: clip a polygon (list of points) against one boundary."""
    out = []
    for i, current in enumerate(polygon):
        previous = polygon[i - 1]
        if inside(current):
            if not inside(previous):
                out.append(cross(previous, current))
            out.append(current)
        elif inside(previous):
            out.append(cross(previous, current))
    return out


def _lerp(a, b, t):
    return a + (b - a) * t


def _footprint(p, camera_triangles, width, height):
    """Where triangles land on the image.

    Returns the points of their outlines clipped to the near plane and the frame, and the extent
    [u0, v0, u1, v1] of the part in front of the eye before frame clipping (to tell which edges cut it).
    Triangles wholly inside the view are used as they are; only those crossing a boundary are clipped.
    """
    near = p.near
    ahead = camera_triangles[..., 2] >= near
    front = camera_triangles[ahead.all(axis=1)]
    crossing = camera_triangles[ahead.any(axis=1) & ~ahead.all(axis=1)]
    extents, points, to_clip = [], [], []
    if len(front):
        uv = _pixels(p, front, width, height).reshape(-1, 3, 2)
        extents.append(uv.reshape(-1, 2))
        within = ((uv[..., 0] >= 0) & (uv[..., 0] <= width) & (uv[..., 1] >= 0) & (uv[..., 1] <= height)).all(axis=1)
        points.append(uv[within].reshape(-1, 2))
        to_clip += [list(t) for t in uv[~within]]
    for tri in crossing:
        polygon = _clip(list(tri), lambda v: v[2] >= near, lambda a, b: _lerp(a, b, (near - a[2]) / (b[2] - a[2])))
        if len(polygon) >= 3:
            uv = _pixels(p, np.array(polygon), width, height)
            extents.append(uv)
            to_clip.append(list(uv))
    bounds = [(0, 0.0, 1), (0, float(width), -1), (1, 0.0, 1), (1, float(height), -1)]
    for polygon in to_clip:
        for axis, value, sign in bounds:
            polygon = _clip(polygon, lambda q, a=axis, v=value, s=sign: s * (q[a] - v) >= 0,
                            lambda a_, b_, a=axis, v=value: _lerp(a_, b_, (v - a_[a]) / (b_[a] - a_[a])))
            if not polygon:
                break
        if polygon:
            points.append(np.array(polygon))
    points = np.concatenate(points) if points else np.zeros((0, 2))
    allext = np.concatenate(extents) if extents else np.zeros((0, 2))
    extent = [*allext.min(axis=0), *allext.max(axis=0)] if len(allext) else None
    return points, extent


def _samples(triangles, eye, solid):
    """Points on the triangles that face the eye: centroids plus three interior points each."""
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    facing = np.einsum("ij,ij->i", normals, eye - triangles.mean(axis=1)) > 0
    tris = triangles[facing | ~solid]
    weights = np.array([[1 / 3, 1 / 3, 1 / 3], [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]])
    points = np.einsum("wk,tkd->twd", weights, tris).reshape(-1, 3)
    if len(points) > MAX_SAMPLES:
        points = points[np.linspace(0, len(points) - 1, MAX_SAMPLES).astype(int)]
    return points


def _third(u, width):
    return "left" if u < width / 3 else "right" if u > 2 * width / 3 else "centre"


def see(scene, p, size=DEFAULT_SIZE):
    """The imagined view: one entry per object, with pixel box, depth, framing and a reason code."""
    width, height = size
    result = {"perspective": p.summary(), "size": [width, height], "objects": []}
    if p.kind == "Viewpoint":
        f = focal_px(p, width, height)
        result["focal_px"] = round(f, 2)
        result["horizontal_fov_deg"] = round(math.degrees(2 * math.atan(width / 2 / f)), 2)
    if p.falls:
        result["background_only"] = True
        result["reason"] = "VIEWER_FALLS: WALK gravity with no support under the Viewpoint"
        return result

    occluders = [s for s in scene.shapes if s.rendered and len(s.triangles) and s.transparency < OPAQUE_BELOW]
    occ_tris = np.concatenate([s.triangles for s in occluders]) if occluders else np.zeros((0, 3, 3))
    occ_owner = np.array([s.object for s in occluders for _ in range(len(s.triangles))])
    occ_solid = np.concatenate([np.full(len(s.triangles), s.solid) for s in occluders]) if occluders else np.zeros(0, bool)

    for name, object_shapes in scene.objects().items():
        result["objects"].append(_see_object(p, name, object_shapes, width, height, scene.fog_range,
                                             occ_tris, occ_owner, occ_solid))
    result["background_only"] = not any(o.get("status") == "VISIBLE" for o in result["objects"])
    return result


def _see_object(p, name, object_shapes, width, height, fog_range, occ_tris, occ_owner, occ_solid):
    entry = {"name": name, "geometry": sorted({s.geometry for s in object_shapes})}
    drawn = [s for s in object_shapes if s.rendered and len(s.triangles)]
    if not drawn:
        entry["status"] = "NOT_RENDERED"
        return entry
    tris = np.concatenate([s.triangles for s in drawn])
    solid = np.concatenate([np.full(len(s.triangles), s.solid) for s in drawn])
    points = tris.reshape(-1, 3)
    center = (points.min(axis=0) + points.max(axis=0)) / 2
    entry["distance_m"] = round(float(np.linalg.norm(center - p.eye)), 3)
    entry["center_world_m"] = [round(float(x), 3) for x in center]
    cam = to_camera(p, points).reshape(-1, 3, 3)
    ahead = cam[..., 2] >= p.near
    if not ahead.any():
        entry["status"] = "OUT_OF_FRUSTUM"
        entry["where"] = "behind the viewer"
        return entry
    nearest = float(max(p.near, cam[..., 2][ahead].min()))
    entry["depth_m"] = {"nearest": round(nearest, 3), "center": round(float(to_camera(p, center[None])[0, 2]), 3)}
    if nearest > p.far:
        entry["status"] = "BEYOND_FAR"
        return entry
    if (~ahead).any():
        entry["near_clipped"] = True
    in_frame, extent = _footprint(p, cam, width, height)
    center_cam = to_camera(p, center[None])
    if center_cam[0, 2] > 0:
        cu, cv = _pixels(p, center_cam, width, height)[0]
        entry["center_px"] = [round(float(cu), 1), round(float(cv), 1)]
    if len(in_frame) == 0:
        u0, v0, u1, v1 = extent
        entry["status"] = "OUT_OF_FRUSTUM"
        entry["where"] = ("left of" if u1 < 0 else "right of" if u0 > width else "above" if v1 < 0 else "below") + " the frame"
        return entry
    box = [*in_frame.min(axis=0), *in_frame.max(axis=0)]
    entry["pixel_box"] = [round(float(x), 1) + 0.0 for x in box]      # + 0.0 turns -0.0 into 0.0
    entry["cut_off"] = [side for side, off in zip(("left", "top", "right", "bottom"),
                                                  (extent[0] < -0.5, extent[1] < -0.5, extent[2] > width + 0.5,
                                                   extent[3] > height + 0.5)) if off]
    entry["size_px"] = [round(float(box[2] - box[0]), 1), round(float(box[3] - box[1]), 1)]
    entry["frame_height_fraction"] = round(float((box[3] - box[1]) / height), 3)
    entry["third"] = _third((box[0] + box[2]) / 2, width)
    visible, blockers = _visibility(p, tris, solid, name, occ_tris, occ_owner, occ_solid, width, height)
    entry["visible_fraction"] = visible
    if blockers:
        entry["occluded_by"] = blockers
    if fog_range and nearest > fog_range:
        entry["status"] = "FOGGED"
    elif visible == 0:
        entry["status"] = f"OCCLUDED_BY({blockers[0]})" if blockers else "OCCLUDED"
    elif entry["size_px"][0] < 2 and entry["size_px"][1] < 2:
        entry["status"] = "TOO_SMALL"
    else:
        entry["status"] = "VISIBLE"
    return entry


def _visibility(p, tris, solid, name, occ_tris, occ_owner, occ_solid, width, height):
    """Fraction of sampled surface points with a clear line of sight, and what blocks the rest."""
    points = _samples(tris, p.eye, solid)
    uv, depth = project(p, points, width, height)
    inside = (depth >= p.near) & (depth <= p.far) & (uv[:, 0] >= 0) & (uv[:, 0] <= width) & (uv[:, 1] >= 0) & (uv[:, 1] <= height)
    points = points[inside]
    if len(points) == 0:
        return None, []
    others = occ_owner != name
    if not others.any():
        return 1.0, []
    vectors = points - p.eye
    distance = np.linalg.norm(vectors, axis=1)
    _, index = geometry.raycast(np.broadcast_to(p.eye, points.shape), vectors / distance[:, None],
                                occ_tris[others], cull_back=occ_solid[others], max_t=distance - 1e-4)
    blocked = index >= 0
    counts = {}
    for n in occ_owner[others][index[blocked]]:
        counts[n] = counts.get(n, 0) + 1
    return round(float(1 - blocked.mean()), 3), sorted(counts, key=counts.get, reverse=True)
