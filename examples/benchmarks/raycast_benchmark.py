"""Benchmark BVH vs brute-force raycast on structured (non-uniform) scenes.

Generates several scene classes:
 - clustered: several dense clusters of triangles
 - terrain: a grid heightfield triangulation
 - room-like: collection of box-like clusters

And workloads:
 - camera rays: originate at a camera and sample a frustum
 - directional rays: coherent parallel rays (e.g., shadow queries)
 - random rays: uniformly random origins and directions

Saves and prints results showing brute time, BVH build+query time, and amortized speedups.
"""

import csv
import time
from pathlib import Path

import numpy as np

from x3d_perspective import geometry

OUT = Path(__file__).parent


def make_clustered(n_triangles=2000, n_clusters=8, cluster_radius=1.0, cluster_spread=10.0, seed=0):
    rng = np.random.default_rng(seed)
    tris = []
    per_cluster = max(1, n_triangles // n_clusters)
    for i in range(n_clusters):
        center = rng.normal(scale=cluster_spread, size=3)
        for _ in range(per_cluster):
            # small triangle near the center
            a = center + rng.normal(scale=cluster_radius * 0.1, size=3)
            b = center + rng.normal(scale=cluster_radius * 0.1, size=3)
            c = center + rng.normal(scale=cluster_radius * 0.1, size=3)
            tris.append([a, b, c])
    tris = np.array(tris, dtype=float)
    return tris


def make_terrain(nx=128, nz=128, scale=1.0, height=2.0, seed=0):
    rng = np.random.default_rng(seed)
    xs = np.linspace(0, nx * scale, nx)
    zs = np.linspace(0, nz * scale, nz)
    xv, zv = np.meshgrid(xs, zs)
    # simple Perlin-like noise via multiple frequencies
    y = (rng.standard_normal(size=xv.shape) * 0.5)
    y += (rng.standard_normal(size=xv.shape) * 0.2).astype(float)
    y = (y - y.min()) / (y.max() - y.min()) * height
    tris = []
    for i in range(nx - 1):
        for j in range(nz - 1):
            p0 = np.array([xv[j, i], y[j, i], zv[j, i]])
            p1 = np.array([xv[j, i + 1], y[j, i + 1], zv[j, i + 1]])
            p2 = np.array([xv[j + 1, i], y[j + 1, i], zv[j + 1, i]])
            p3 = np.array([xv[j + 1, i + 1], y[j + 1, i + 1], zv[j + 1, i + 1]])
            tris.append([p0, p1, p2])
            tris.append([p1, p3, p2])
    return np.array(tris, dtype=float)


def make_room_like(n_boxes=50, box_triangles=100, room_size=20.0, seed=0):
    rng = np.random.default_rng(seed)
    tris = []
    for _ in range(n_boxes):
        center = rng.uniform(-room_size / 2, room_size / 2, size=3)
        sx, sy, sz = rng.uniform(0.2, 2.0, size=3)
        # create a box via 12 triangles
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        corners = np.array([[cx, cy, cz] for cx in (-hx, hx) for cy in (-hy, hy) for cz in (-hz, hz)]) + center
        faces = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
        for f in faces:
            tris.append([corners[f[0]], corners[f[1]], corners[f[2]]])
            tris.append([corners[f[0]], corners[f[2]], corners[f[3]]])
    return np.array(tris, dtype=float)


def camera_rays(camera_origin, look_at, up, fov_deg, width, height, n_samples, seed=0):
    rng = np.random.default_rng(seed)
    # compute camera basis
    forward = np.array(look_at) - np.array(camera_origin)
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)
    upv = np.cross(right, forward)
    aspect = width / height
    fov = np.radians(fov_deg)
    # sample N directions inside the frustum roughly
    dirs = []
    for _ in range(n_samples):
        # sample image plane coords in [-1,1]
        x = rng.uniform(-1, 1) * aspect
        y = rng.uniform(-1, 1)
        z = 1.0 / np.tan(fov / 2)
        d = (forward * z + right * x + upv * y)
        d = d / np.linalg.norm(d)
        dirs.append(d)
    origins = np.tile(np.array(camera_origin), (n_samples, 1))
    return origins, np.array(dirs)


def directional_rays(direction, bbox_center, bbox_size, n_rays=1024, seed=0):
    rng = np.random.default_rng(seed)
    # origins sampled in a plane across bbox to hit many triangles
    origins = rng.uniform(bbox_center - bbox_size / 2, bbox_center + bbox_size / 2, size=(n_rays, 3))
    dirs = np.tile(np.array(direction) / np.linalg.norm(direction), (n_rays, 1))
    return origins, dirs


def random_rays(n_rays, radius=50.0, seed=0):
    rng = np.random.default_rng(seed)
    origins = rng.uniform(-radius, radius, size=(n_rays, 3))
    dirs = rng.normal(size=(n_rays, 3))
    dirs /= np.linalg.norm(dirs, axis=1)[:, None]
    return origins, dirs


def run_bench(triangles, origins, dirs, chunk=64, repeat_build=False):
    # brute force
    t0 = time.perf_counter()
    geometry.raycast(origins, dirs, triangles, chunk=chunk)
    brute = time.perf_counter() - t0

    # BVH: measure build + query
    t0 = time.perf_counter()
    bvh = geometry._build_bvh(triangles)
    t_build = time.perf_counter() - t0
    t0 = time.perf_counter()
    geometry.raycast(origins, dirs, triangles, chunk=chunk, bvh=bvh)
    bvh_query = time.perf_counter() - t0
    return {
        "triangles": len(triangles),
        "rays": len(dirs),
        "brute_seconds": brute,
        "bvh_build_seconds": t_build,
        "bvh_query_seconds": bvh_query,
    }


def amortized_speedup(result, amortize_build_over=1):
    brute = result["brute_seconds"]
    bvh_total = result["bvh_build_seconds"] / amortize_build_over + result["bvh_query_seconds"]
    return brute / bvh_total if bvh_total > 0 else float("inf")


def main():
    configs = [
        ("clustered", make_clustered, {"n_triangles": 4000, "n_clusters": 8}),
        ("terrain", make_terrain, {"nx": 128, "nz": 128}),
        ("room", make_room_like, {"n_boxes": 200}),
    ]

    workloads = [
        ("camera", lambda tris: camera_rays([0, 10, -30], [0, 0, 0], np.array([0, 1, 0]), 60, 16, 16, 1024)),
        ("directional", lambda tris: directional_rays([0, -1, 0], np.array([0, 0, 0]), np.array([50, 50, 50]), 1024)),
        ("random", lambda tris: random_rays(1024)),
    ]

    rows = []
    for name, maker, kwargs in configs:
        print(f"\nScene: {name} -- generating")
        tris = maker(**kwargs)
        print(f" triangles: {len(tris)}")
        # tuning sweep for leaf sizes and methods
        leaf_sizes = [4, 8, 12, 24, 48]
        methods = ["median", "sah"]
        tuning_results = []
        for method in methods:
            for leaf in leaf_sizes:
                # build once and run a small directional workload to measure
                origins, dirs = directional_rays([0, -1, 0], np.array([0, 0, 0]), np.array([50, 50, 50]), 512)
                t0 = time.perf_counter(); bvh = geometry._build_bvh(tris, method=method, leaf_size=leaf); build=time.perf_counter()-t0
                t0=time.perf_counter(); geometry.raycast(origins, dirs, tris, chunk=64, bvh=bvh); q=time.perf_counter()-t0
                tuning_results.append((method, leaf, build, q))
        # pick best method/leaf by build+query
        best = min(tuning_results, key=lambda x: x[2] + x[3])
        print(f" best tuning: method={best[0]} leaf={best[1]} build+query={best[2]+best[3]:0.3f}s")

        for wname, wgen in workloads:
            print(f" workload: {wname}")
            origins, dirs = wgen(tris)
            res = run_bench(tris, origins, dirs, chunk=64)
            for a in (1, 5, 10, 30):
                rows.append({
                    "scene": name,
                    "workload": wname,
                    "triangles": res["triangles"],
                    "rays": res["rays"],
                    "amortize_over": a,
                    "brute_seconds": res["brute_seconds"],
                    "bvh_build_seconds": res["bvh_build_seconds"],
                    "bvh_query_seconds": res["bvh_query_seconds"],
                    "amortized_speedup": amortized_speedup(res, a),
                    "best_method": best[0],
                    "best_leaf": best[1],
                })
                print(f"  amortize over {a:2d}: speedup={amortized_speedup(res, a):0.2f}x")

    out = OUT / "nonuniform_bvh_results.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"\nResults written to: {out}")


if __name__ == "__main__":
    main()
