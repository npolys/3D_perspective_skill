"""Triangles for X3D geometry nodes, and ray casting against them.

Triangles are (n, 3, 3) arrays. Winding follows X3D: counterclockwise is the front face when
ccw is TRUE. Primitives are closed and convex, so their triangles are wound to face outward.
"""

import math

import numpy as np

SEGMENTS = 32

# BVH tuning defaults
BVH_DEFAULT_METHOD = "median"
BVH_DEFAULT_LEAF = 24


def _outward(triangles, inside):
    """Wind each triangle of a convex solid so its normal points away from an inside point."""
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    flip = np.einsum("ij,ij->i", normals, triangles.mean(axis=1) - inside) < 0
    triangles[flip] = triangles[flip][:, ::-1]
    return triangles


def _quads(quads):
    """Split quads (n, 4, 3) into triangles."""
    quads = np.asarray(quads, dtype=float)
    return np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])


def box(size):
    hx, hy, hz = (s / 2 for s in size)
    c = np.array([[x, y, z] for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)])
    faces = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    return _outward(_quads(c[faces]), np.zeros(3))


def sphere(radius, segments=SEGMENTS, rings=SEGMENTS // 2):
    theta = np.linspace(0, math.pi, rings + 1)
    phi = np.linspace(0, 2 * math.pi, segments + 1)
    grid = np.stack([np.outer(np.sin(theta), np.sin(phi)), np.outer(np.cos(theta), np.ones_like(phi)),
                     np.outer(np.sin(theta), np.cos(phi))], axis=-1) * radius
    quads = np.stack([grid[:-1, :-1], grid[1:, :-1], grid[1:, 1:], grid[:-1, 1:]], axis=2).reshape(-1, 4, 3)
    return _outward(_quads(quads), np.zeros(3))


def _ring(radius, y, segments):
    a = np.linspace(0, 2 * math.pi, segments, endpoint=False)
    return np.stack([radius * np.sin(a), np.full(segments, y), radius * np.cos(a)], axis=1)


def _cap(ring, y):
    center = np.array([0.0, y, 0.0])
    return np.stack([np.broadcast_to(center, ring.shape), ring, np.roll(ring, -1, axis=0)], axis=1)


def cylinder(radius, height, bottom=True, top=True, side=True, segments=SEGMENTS):
    lower, upper = _ring(radius, -height / 2, segments), _ring(radius, height / 2, segments)
    parts = []
    if side:
        parts.append(_quads(np.stack([lower, np.roll(lower, -1, 0), np.roll(upper, -1, 0), upper], axis=1)))
    if bottom:
        parts.append(_cap(lower, -height / 2))
    if top:
        parts.append(_cap(upper, height / 2))
    return _outward(np.concatenate(parts), np.zeros(3)) if parts else np.zeros((0, 3, 3))


def cone(bottom_radius, height, bottom=True, side=True, segments=SEGMENTS):
    base = _ring(bottom_radius, -height / 2, segments)
    parts = []
    if side:
        apex = np.array([0.0, height / 2, 0.0])
        parts.append(np.stack([base, np.roll(base, -1, 0), np.broadcast_to(apex, base.shape)], axis=1))
    if bottom:
        parts.append(_cap(base, -height / 2))
    return _outward(np.concatenate(parts), np.array([0.0, -height / 4, 0.0])) if parts else np.zeros((0, 3, 3))


def polygons(points, index, ccw=True):
    """Fan-triangulate an IndexedFaceSet coordIndex list (polygons separated by -1)."""
    points = np.asarray(points, dtype=float).reshape(-1, 3)
    triangles, face = [], []
    for i in list(index) + [-1]:
        if i >= 0:
            face.append(i)
            continue
        triangles += [[face[0], face[k], face[k + 1]] for k in range(1, len(face) - 1)]
        face = []
    tris = points[np.array(triangles, dtype=int)] if triangles else np.zeros((0, 3, 3))
    return tris if ccw else tris[:, ::-1]


def indexed(points, index, per_face, ccw=True):
    """IndexedTriangleSet (per_face 3) or IndexedQuadSet (per_face 4)."""
    points = np.asarray(points, dtype=float).reshape(-1, 3)
    faces = points[np.asarray(index, dtype=int)[: len(index) // per_face * per_face].reshape(-1, per_face)]
    tris = faces if per_face == 3 else _quads(faces)
    return tris if ccw else tris[:, ::-1]


def elevation_grid(x_dimension, z_dimension, x_spacing, z_spacing, heights, ccw=True):
    h = np.asarray(heights, dtype=float).reshape(z_dimension, x_dimension)
    xs, zs = np.meshgrid(np.arange(x_dimension) * x_spacing, np.arange(z_dimension) * z_spacing)
    grid = np.stack([xs, h, zs], axis=-1)
    quads = np.stack([grid[:-1, :-1], grid[1:, :-1], grid[1:, 1:], grid[:-1, 1:]], axis=2).reshape(-1, 4, 3)
    tris = _quads(quads)
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    up = normals[:, 1] > 0
    tris[~up] = tris[~up][:, ::-1]           # front faces point up when ccw is TRUE
    return tris if ccw else tris[:, ::-1]


def _triangle_bounds(triangles):
    """Axis-aligned bounds for a triangle array: (min_xyz, max_xyz)."""
    mins = triangles.min(axis=1)
    maxs = triangles.max(axis=1)
    return mins.min(axis=0), maxs.max(axis=0)


def _aabb_hit(origin, direction, min_xyz, max_xyz, t_max):
    """Return True when a ray hits the axis-aligned box before t_max."""
    t_min = 0.0
    t_max = float(t_max)
    for axis in range(3):
        if abs(direction[axis]) < 1e-12:
            if origin[axis] < min_xyz[axis] or origin[axis] > max_xyz[axis]:
                return False
            continue
        inv = 1.0 / direction[axis]
        lo = (min_xyz[axis] - origin[axis]) * inv
        hi = (max_xyz[axis] - origin[axis]) * inv
        t_min = max(t_min, min(lo, hi))
        t_max = min(t_max, max(lo, hi))
        if t_max < t_min:
            return False
    return t_max >= max(t_min, 0.0)


def _triangle_hit(origin, direction, triangle, cull_back=False, max_t=np.inf, eps=1e-9):
    """Single triangle hit test for a ray; returns (t, hit)."""
    v0 = triangle[0]
    e1 = triangle[1] - v0
    e2 = triangle[2] - v0
    p = np.cross(direction, e2)
    det = float(np.dot(p, e1))
    if abs(det) <= eps:
        return np.inf, False
    if cull_back and det < 0:
        return np.inf, False
    inv = 1.0 / det
    s = origin - v0
    u = float(np.dot(s, p)) * inv
    if u < -eps or u > 1.0 + eps:
        return np.inf, False
    q = np.cross(s, e1)
    v = float(np.dot(q, direction)) * inv
    if v < -eps or u + v > 1.0 + eps:
        return np.inf, False
    t = float(np.dot(q, e2)) * inv
    if t <= eps or t >= max_t:
        return np.inf, False
    return t, True


import time
from . import config


def _build_bvh(triangles, indices=None, method='median', leaf_size=12):
    """A simple axis-aligned bounding volume hierarchy for triangle sets.

    method: 'median' (fast median-split) or 'sah' (approximate SAH with candidate splits)
    leaf_size: maximum triangles in a leaf.
    """
    instrument = config.get_instrumentation()
    t0 = time.perf_counter() if instrument else None
    if len(triangles) == 0:
        if instrument:
            # still record a fast build
            _metrics['build_count'] += 1
            _metrics['build_time'] += 0.0
        return None
    idx = np.arange(len(triangles)) if indices is None else np.asarray(indices, dtype=int)
    tri = triangles[idx]
    mins = tri.min(axis=1)
    maxs = tri.max(axis=1)
    node_min = mins.min(axis=0)
    node_max = maxs.max(axis=0)
    if len(idx) <= leaf_size:
        node = {"bounds": np.array([node_min, node_max]), "left": None, "right": None, "indices": idx}
        if instrument:
            _metrics['build_count'] += 1
            _metrics['build_time'] += time.perf_counter() - t0
        return node

    centers = (mins + maxs) / 2.0
    extents = node_max - node_min
    axis = int(np.argmax(extents))

    if method == 'median':
        order = np.argsort(centers[:, axis])
        left_idx = idx[order[:len(order) // 2]]
        right_idx = idx[order[len(order) // 2:]]
    else:
        # approximate SAH: evaluate candidate splits along chosen axis using centroid positions
        # choose up to 16 candidates at percentiles
        n_candidates = min(16, len(centers) - 1)
        if n_candidates < 1:
            # fallback to median
            order = np.argsort(centers[:, axis])
            left_idx = idx[order[:len(order) // 2]]
            right_idx = idx[order[len(order) // 2:]]
        else:
            cents = centers[:, axis]
            qs = np.linspace(0.01, 0.99, n_candidates)
            best_cost = float('inf')
            best_split = None
            # precompute triangle bounds for quick left/right box computations
            for q in qs:
                split_val = np.quantile(cents, q)
                left_mask = cents <= split_val
                if left_mask.sum() == 0 or left_mask.sum() == len(cents):
                    continue
                left_idx_candidate = idx[left_mask]
                right_idx_candidate = idx[~left_mask]
                left_tris = triangles[left_idx_candidate]
                right_tris = triangles[right_idx_candidate]
                # surface area heuristic proxy: area = surface area of AABB
                left_min = left_tris.min(axis=1).min(axis=0)
                left_max = left_tris.max(axis=1).max(axis=0)
                right_min = right_tris.min(axis=1).min(axis=0)
                right_max = right_tris.max(axis=1).max(axis=0)
                left_area = np.prod(left_max - left_min + 1e-12)
                right_area = np.prod(right_max - right_min + 1e-12)
                cost = left_area * len(left_idx_candidate) + right_area * len(right_idx_candidate)
                if cost < best_cost:
                    best_cost = cost
                    best_split = (left_idx_candidate, right_idx_candidate)
            if best_split is None:
                order = np.argsort(centers[:, axis])
                left_idx = idx[order[:len(order) // 2]]
                right_idx = idx[order[len(order) // 2:]]
            else:
                left_idx, right_idx = best_split

    node = {
        "bounds": np.array([node_min, node_max]),
        "left": _build_bvh(triangles, left_idx, method=method, leaf_size=leaf_size),
        "right": _build_bvh(triangles, right_idx, method=method, leaf_size=leaf_size),
        "indices": idx,
    }
    if instrument:
        _metrics['build_count'] += 1
        _metrics['build_time'] += time.perf_counter() - t0
    return node


def _bvh_hit(origin, direction, triangles, node, max_t):
    if node is None:
        return np.inf, -1
    instrument = config.get_instrumentation()
    if instrument:
        _metrics['bvh_node_visits'] += 1
    min_xyz, max_xyz = node["bounds"][0], node["bounds"][1]
    if not _aabb_hit(origin, direction, min_xyz, max_xyz, max_t):
        return np.inf, -1
    best_t = np.inf
    best_i = -1
    if node["left"] is None and node["right"] is None:
        # leaf: test all triangles in the leaf
        if instrument:
            _metrics['triangles_tested'] += len(node['indices'])
        for idx in node["indices"]:
            t, hit = _triangle_hit(origin, direction, triangles[idx], False, max_t)
            if hit and t < best_t:
                best_t = t
                best_i = idx
        return best_t, best_i
    left_t, left_i = _bvh_hit(origin, direction, triangles, node["left"], max_t)
    if left_i >= 0:
        best_t = left_t
        best_i = left_i
    right_t, right_i = _bvh_hit(origin, direction, triangles, node["right"], max_t)
    if right_i >= 0 and right_t < best_t:
        best_t = right_t
        best_i = right_i
    return best_t, best_i


# instrumentation metrics
_metrics = {
    'build_count': 0,
    'build_time': 0.0,
    'query_count': 0,
    'query_time': 0.0,
    'triangles_tested': 0,
    'bvh_node_visits': 0,
}


def get_metrics(reset=False):
    """Return current instrumentation metrics. If reset is True, zero the counters after returning."""
    m = dict(_metrics)
    if reset:
        reset_metrics()
    return m


def reset_metrics():
    for k in _metrics:
        _metrics[k] = 0 if isinstance(_metrics[k], int) else 0.0


def raycast(origins, directions, triangles, cull_back=None, max_t=None, eps=1e-9, chunk=64, bvh=None):
    """First hit of each ray against triangles (Moller-Trumbore).

    cull_back: optional boolean per triangle; True means only front faces (counterclockwise seen from
    the ray origin) can be hit, as when X3D renders solid geometry. Returns (t, index) per ray, with
    t = inf and index = -1 where nothing is hit before max_t.

    For larger triangle sets, a small BVH is built to reduce the number of triangle tests unless a
    prebuilt bvh is supplied.
    """
    origins = np.atleast_2d(np.asarray(origins, dtype=float))
    directions = np.atleast_2d(np.asarray(directions, dtype=float))
    n = len(origins)
    best_t, best_i = np.full(n, np.inf), np.full(n, -1)
    if len(triangles) == 0:
        return best_t, best_i
    instrument = config.get_instrumentation()
    if len(triangles) >= 128:
        tree = bvh if bvh is not None else _build_bvh(triangles)
        t0 = time.perf_counter() if instrument else None
        _metrics['query_count'] += 1 if instrument else 0
        for start in range(0, n, chunk):
            o, d = origins[start:start + chunk], directions[start:start + chunk]
            for i, (origin, direction) in enumerate(zip(o, d, strict=True)):
                t_max = np.inf if max_t is None else float(np.asarray(max_t)[start + i])
                t, idx = _bvh_hit(origin, direction, triangles, tree, t_max)
                if idx >= 0:
                    best_t[start + i] = t
                    best_i[start + i] = idx
        if instrument:
            _metrics['query_time'] += time.perf_counter() - t0
        return best_t, best_i
    v0 = triangles[:, 0]
    e1, e2 = triangles[:, 1] - v0, triangles[:, 2] - v0
    limit = np.full(n, np.inf) if max_t is None else np.broadcast_to(np.asarray(max_t, dtype=float), (n,))
    t0 = time.perf_counter() if instrument else None
    _metrics['query_count'] += 1 if instrument else 0
    for start in range(0, n, chunk):
        o, d = origins[start:start + chunk], directions[start:start + chunk]
        # count triangle tests conservatively: all triangles are tested per ray in this path
        if instrument:
            _metrics['triangles_tested'] += triangles.shape[0] * len(o)
        p = np.cross(d[:, None, :], e2[None, :, :])
        det = np.einsum("rtk,tk->rt", p, e1)
        ok = np.abs(det) > eps
        if cull_back is not None:
            ok &= ~(cull_back[None, :] & (det < 0))
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        s = o[:, None, :] - v0[None, :, :]
        u = np.einsum("rtk,rtk->rt", s, p) * inv
        q = np.cross(s, e1[None, :, :])
        v = np.einsum("rtk,rk->rt", q, d) * inv
        t = np.einsum("rtk,tk->rt", q, e2) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-7) & (t < limit[start:start + chunk, None])
        t = np.where(hit, t, np.inf)
        idx = np.argmin(t, axis=1)
        best = t[np.arange(len(o)), idx]
        best_t[start:start + chunk] = best
        best_i[start:start + chunk] = np.where(np.isfinite(best), idx, -1)
    if instrument:
        _metrics['query_time'] += time.perf_counter() - t0
    return best_t, best_i
