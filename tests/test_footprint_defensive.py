import numpy as np

from x3d_perspective import view


class P:
    pass


def test_footprint_empty_returns_no_extent():
    p = P()
    p.near = 0.1
    # empty set of camera-space triangles
    camera_triangles = np.zeros((0, 3, 3))
    points, extent = view._footprint(p, camera_triangles, 1280, 720)
    assert points.shape[0] == 0
    assert extent is None
