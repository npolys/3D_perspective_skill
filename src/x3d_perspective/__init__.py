"""x3d-perspective: take the user's perspective on an X3D scene.

Imagine the 2D view an X3D browser renders from a Viewpoint, capture and see it in X_ITE or X3DOM,
and turn viewer-relative instructions ("put that box to the right of the sphere") into X3D field
changes. See docs/API.md for a guide, and docs/X3D_MAPPINGS.md for the X3D rules implemented.

    import x3d_perspective as xp

    scene = xp.load("room.x3d")
    p = xp.from_viewpoint(scene, "Side", renderer="x3dom")
    view = xp.see(scene, p)                               # where each object lands in 1280x720
    plan = xp.place(scene, p, "Table", "right of", "Lamp")
    plan["set_field"]                                     # {"def": "Table", "field": "translation", ...}

Live capture and verification (x3d_perspective.live, x3d_perspective.verify) need the `live` extra.
"""

__version__ = "7.0.1"

from .frames import frame
from .perspective import Perspective, from_viewpoint
from .relations import place, relations_between, resolve
from .schema import PerspectiveModel, build_perspective_model, validate_perspective_model
from .view import DEFAULT_SIZE, see
from .x3d_loader import Scene, load

__all__ = [
    "DEFAULT_SIZE", "Perspective", "PerspectiveModel", "Scene", "__version__", "build_perspective_model",
    "frame", "from_viewpoint", "load", "place", "relations_between", "resolve", "see",
    "validate_perspective_model",
]
