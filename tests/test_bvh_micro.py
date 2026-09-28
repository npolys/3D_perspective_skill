import numpy as np
from x3d_perspective import geometry
import time


def make_clustered(n_triangles=2000, n_clusters=8, seed=0):
    rng = np.random.default_rng(seed)
    tris = []
    per = max(1, n_triangles // n_clusters)
    for i in range(n_clusters):
        center = rng.normal(scale=10.0, size=3)
        for _ in range(per):
            a = center + rng.normal(scale=0.1, size=3)
            b = center + rng.normal(scale=0.1, size=3)
            c = center + rng.normal(scale=0.1, size=3)
            tris.append([a, b, c])
    return np.array(tris, dtype=float)


def test_bvh_speedup_and_equivalence():
    tris = make_clustered(4000, 8)
    origins = np.zeros((256, 3))
    dirs = np.tile(np.array([0.0, -1.0, 0.0]), (256, 1))
    # brute
    t0 = time.perf_counter()
    t_b, i_b = geometry.raycast(origins, dirs, tris, chunk=64)
    brute = time.perf_counter() - t0
    # bvh
    t0 = time.perf_counter()
    bvh = geometry._build_bvh(tris, method='median', leaf_size=24)
    build = time.perf_counter() - t0
    t0 = time.perf_counter()
    t_v, i_v = geometry.raycast(origins, dirs, tris, chunk=64, bvh=bvh)
    bvhq = time.perf_counter() - t0
    # equivalence
    assert np.allclose(t_b, t_v)
    assert (i_b == i_v).all()
    # check amortized speedup over 5 frames
    amort = brute / (build / 5 + bvhq)
    assert amort >= 1.05
