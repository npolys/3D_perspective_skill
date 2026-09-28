"""Vector, rotation and transform helpers for X3D field values."""

import math

import numpy as np


def floats(text):
    """Parse an X3D numeric field value such as "1 2 3" (commas allowed) into floats."""
    return [float(token) for token in text.replace(",", " ").split()]


def normalize(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def rotation(axis_angle):
    """3x3 matrix for an SFRotation (x y z angle), by Rodrigues' formula."""
    x, y, z, angle = axis_angle
    axis = np.array([x, y, z], dtype=float)
    n = np.linalg.norm(axis)
    if n == 0 or angle == 0:
        return np.eye(3)
    kx, ky, kz = axis / n
    k = np.array([[0, -kz, ky], [kz, 0, -kx], [-ky, kx, 0]])
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * k @ k


def sfrotation(r):
    """SFRotation (x y z angle) for a 3x3 rotation matrix."""
    angle = math.acos(max(-1.0, min(1.0, (np.trace(r) - 1) / 2)))
    if angle < 1e-9:
        return (0.0, 0.0, 1.0, 0.0)
    if math.pi - angle < 1e-6:
        # At 180 degrees R = 2kk^T - I: take the axis from the diagonal, signs from the largest row.
        k = np.sqrt(np.maximum((np.diag(r) + 1) / 2, 0))
        i = int(np.argmax(k))
        for j in range(3):
            if j != i:
                k[j] = math.copysign(k[j], r[i, j])
        return (*normalize(k), angle)
    axis = np.array([r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]])
    return (*normalize(axis), angle)


def translate(t):
    m = np.eye(4)
    m[:3, 3] = t
    return m


def linear(r):
    m = np.eye(4)
    m[:3, :3] = r
    return m


def uniform_scale(s):
    return linear(np.diag([s, s, s]))


def transform_matrix(translation, rotation_, scale, scale_orientation, center):
    """Local-to-parent matrix of an X3D Transform: P' = T * C * R * SR * S * -SR * -C * P."""
    sr = rotation(scale_orientation)
    return (translate(translation) @ translate(center) @ linear(rotation(rotation_)) @ linear(sr)
            @ linear(np.diag(scale)) @ linear(sr.T) @ translate(-np.asarray(center, dtype=float)))


def apply(m, points):
    """Transform points (n x 3) by a 4x4 matrix."""
    points = np.asarray(points, dtype=float)
    return points @ m[:3, :3].T + m[:3, 3]


def frame_rotation(m):
    """Rotation part of a 4x4 matrix with scale removed (polar decomposition)."""
    u, _, vt = np.linalg.svd(m[:3, :3])
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] *= -1
        r = u @ vt
    return r


def axis_scales(m):
    """Length each local axis is stretched to by a 4x4 matrix."""
    return np.linalg.norm(m[:3, :3], axis=0)
