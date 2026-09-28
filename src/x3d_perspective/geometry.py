"""Triangles for X3D geometry nodes, and ray casting against them.

Triangles are (n, 3, 3) arrays. Winding follows X3D: counterclockwise is the front face when
ccw is TRUE. Primitives are closed and convex, so their triangles are wound to face outward.
"""

import math

import numpy as np

SEGMENTS = 32


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


def raycast(origins, directions, triangles, cull_back=None, max_t=None, eps=1e-9, chunk=64):
    """First hit of each ray against triangles (Moller-Trumbore).

    cull_back: optional boolean per triangle; True means only front faces (counterclockwise seen from
    the ray origin) can be hit, as when X3D renders solid geometry. Returns (t, index) per ray, with
    t = inf and index = -1 where nothing is hit before max_t.
    """
    origins = np.atleast_2d(np.asarray(origins, dtype=float))
    directions = np.atleast_2d(np.asarray(directions, dtype=float))
    n = len(origins)
    best_t, best_i = np.full(n, np.inf), np.full(n, -1)
    if len(triangles) == 0:
        return best_t, best_i
    v0 = triangles[:, 0]
    e1, e2 = triangles[:, 1] - v0, triangles[:, 2] - v0
    limit = np.full(n, np.inf) if max_t is None else np.broadcast_to(np.asarray(max_t, dtype=float), (n,))
    for start in range(0, n, chunk):
        o, d = origins[start:start + chunk], directions[start:start + chunk]
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
    return best_t, best_i
