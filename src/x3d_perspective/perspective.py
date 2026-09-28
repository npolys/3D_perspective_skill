"""The viewer's perspective: the bound Viewpoint, the body from NavigationInfo, and the WALK eye.

See docs/X3D_MAPPINGS.md §1 and §4 for the rules implemented here.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from . import geometry, mathx, x3d_loader

# Whether a renderer applies WALK gravity and terrain following as soon as a Viewpoint is bound.
# The spec gives no timing, so this is measured per renderer (tests/test_live.py, 2026-09-28):
# X_ITE drops the eye onto support on bind; X3DOM 1.8.3 keeps the authored eye until the user moves.
SETTLES_ON_BIND = {"spec": True, "x_ite": True, "x3dom": False}


@dataclass
class Perspective:
    viewpoint: str
    description: str
    renderer: str
    kind: str
    navigation_type: list
    walk: bool
    authored_eye: np.ndarray
    eye: np.ndarray | None          # effective eye in meters; None when the viewer falls
    right: np.ndarray
    camera_up: np.ndarray
    forward: np.ndarray
    up: np.ndarray                  # +Y of the Viewpoint's parent frame
    field_of_view: object
    near: float
    far: float
    collision_radius: float
    eye_height: float
    step_height: float
    speed: float
    headlight: bool
    support: str | None = None
    falls: bool = False
    notes: list = field(default_factory=list)

    @property
    def gravity(self):
        return -self.up

    def level(self):
        """View direction flattened onto the ground plane (the top of the image when looking straight down)."""
        flat = self.forward - np.dot(self.forward, self.up) * self.up
        if np.linalg.norm(flat) < 1e-6:
            flat = self.camera_up if np.dot(self.forward, self.up) < 0 else -self.camera_up
        return mathx.normalize(flat)

    def directions(self):
        """Viewer-relative direction words as world vectors (docs/X3D_MAPPINGS.md §3)."""
        level = self.level()
        right = mathx.normalize(np.cross(level, self.up))
        return {"right of": right, "left of": -right, "behind": level, "in front of": -level,
                "above": self.up, "below": -self.up}

    def summary(self):
        return {
            "viewpoint": self.viewpoint, "description": self.description, "renderer": self.renderer,
            "navigation_type": self.navigation_type, "walk_gravity": self.walk,
            "authored_eye_m": _round(self.authored_eye), "eye_m": _round(self.eye), "falls": self.falls,
            "support": self.support, "forward": _round(self.forward), "up": _round(self.up),
            "right": _round(self.directions()["right of"]), "field_of_view": self.field_of_view,
            "near_m": round(self.near, 4), "far_m": None if math.isinf(self.far) else round(self.far, 4),
            "body_m": {"collision_radius": round(self.collision_radius, 4), "eye_height": round(self.eye_height, 4),
                       "step_height": round(self.step_height, 4)},
            "speed_m_s": round(self.speed, 4), "headlight": self.headlight, "notes": self.notes,
        }


def _round(v, digits=4):
    return None if v is None else [round(float(x), digits) for x in v]


def default_viewpoint():
    """The camera a browser uses when the scene has no Viewpoint: the spec defaults (describe_node)."""
    t = "Viewpoint"
    return x3d_loader.Viewpoint(
        name="(default)", kind=t, description="X3D default camera",
        position=np.array(mathx.floats(x3d_loader.default(t, "position"))),
        orientation=tuple(mathx.floats(x3d_loader.default(t, "orientation"))),
        field_of_view=float(x3d_loader.default(t, "fieldOfView")),
        near_distance=float(x3d_loader.default(t, "nearDistance")), far_distance=float(x3d_loader.default(t, "farDistance")),
        parent_matrix=np.eye(4))


def from_viewpoint(scene, name=None, renderer="spec"):
    """The perspective a renderer shows when this Viewpoint (default: the initially bound one) is bound."""
    vp = scene.viewpoint(name) if scene.viewpoints else None
    if vp is None:
        if name:
            raise KeyError(f"the scene has no Viewpoints, so none named {name!r}")
        vp = default_viewpoint()
    unit = scene.unit
    to_meters = mathx.uniform_scale(unit) @ vp.parent_matrix
    frame = mathx.frame_rotation(vp.parent_matrix)
    scales = mathx.axis_scales(vp.parent_matrix)
    s = float(scales.mean())
    camera = frame @ mathx.rotation(vp.orientation)
    nav = scene.bound_navigation_info(vp)
    radius, height, step = (x * s * unit for x in (nav.avatar_size + [0.25, 1.6, 0.75][len(nav.avatar_size):])[:3])
    near = vp.near_distance * s * unit if vp.near_distance > 0 else radius / 2
    if vp.far_distance > 0:
        far = vp.far_distance * s * unit
    else:
        far = nav.visibility_limit * s * unit if nav.visibility_limit > 0 else math.inf
    authored = mathx.apply(to_meters, vp.position[None])[0]
    walk = bool(nav.type) and nav.type[0].upper() == "WALK"
    p = Perspective(
        viewpoint=vp.name, description=vp.description, renderer=renderer, kind=vp.kind, navigation_type=nav.type,
        walk=walk, authored_eye=authored, eye=authored.copy(), right=camera[:, 0], camera_up=camera[:, 1],
        forward=-camera[:, 2], up=mathx.normalize(frame @ np.array([0.0, 1.0, 0.0])),
        field_of_view=vp.field_of_view, near=near, far=far, collision_radius=radius, eye_height=height,
        step_height=step, speed=nav.speed * s * unit, headlight=nav.headlight)
    if np.ptp(scales) > 1e-6 * max(s, 1.0):
        p.notes.append("the Viewpoint's parent frame is scaled non-uniformly; the body uses the mean scale")
    if walk:
        settles = SETTLES_ON_BIND.get(renderer, True)
        if settles is None:
            p.notes.append(f"{renderer}: whether WALK gravity applies on bind is not yet measured; assuming it does")
        if settles is not False:
            _settle(scene, p)
        else:
            p.notes.append(f"{renderer} keeps the authored eye until the user moves; WALK gravity applies then")
    return p


def _settle(scene, p):
    """WALK: drop the eye along -up onto collidable support, then hold it eye_height above it (§1)."""
    triangles, owners, _ = scene.triangles(collidable=True)
    t, index = geometry.raycast(p.authored_eye[None], p.gravity[None], triangles)
    if index[0] < 0:
        p.falls, p.eye = True, None
        p.notes.append("WALK gravity with no support under the Viewpoint: the viewer falls and the view shows only the Background")
        return
    ground = p.authored_eye + p.gravity * t[0]
    p.eye = ground + p.up * p.eye_height
    p.support = owners[index[0]]
    if not np.allclose(p.eye, p.authored_eye, atol=1e-3):
        p.notes.append(f"WALK: eye moved from the authored height to {p.eye_height:.3f} m above {p.support}")
