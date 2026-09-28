"""Formal schema-shaped output for the perspective skill contract.

This layer bridges the runtime perspective engine with the proposed skill schema by
exposing a compact typed model that can be validated and handed downstream to later
X3D authoring stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import perspective


@dataclass
class CoordinateFrame:
    handedness: str = "right"
    up_axis: str = "+Y"
    right_axis: str = "+X"
    forward_axis: str = "-Z"
    gravity_axis: str = "-Y"
    supports: list[str] = field(
        default_factory=lambda: [
            "local_coordinate_frames",
            "nested_transforms",
            "geospatial_frames",
            "humanoid_frames",
            "object_frames",
        ]
    )


@dataclass
class PerspectiveModel:
    perspective_type: str
    coordinate_frame: CoordinateFrame
    scale_class: str
    navigation_mode: str
    camera_profile: str
    observer_properties: dict[str, Any]
    viewpoints: list[str]
    affordances: list[str]
    accessibility_features: list[str] | None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "perspective_type": self.perspective_type,
            "coordinate_frame": {
                "handedness": self.coordinate_frame.handedness,
                "up_axis": self.coordinate_frame.up_axis,
                "right_axis": self.coordinate_frame.right_axis,
                "forward_axis": self.coordinate_frame.forward_axis,
                "gravity_axis": self.coordinate_frame.gravity_axis,
                "supports": self.coordinate_frame.supports,
            },
            "scale_class": self.scale_class,
            "navigation_mode": self.navigation_mode,
            "camera_profile": self.camera_profile,
            "observer_properties": self.observer_properties,
            "viewpoints": self.viewpoints,
            "affordances": self.affordances,
            "accessibility_features": self.accessibility_features,
            "notes": self.notes,
        }


def _default_coordinate_frame() -> CoordinateFrame:
    return CoordinateFrame()


def _infer_scale_class(scene: Any) -> str:
    """Heuristic scale selection grounded in scene size and runtime context."""
    if getattr(scene, "shapes", None):
        sizes = []
        for shape in scene.shapes:
            if len(shape.triangles) == 0:
                continue
            pts = shape.triangles.reshape(-1, 3)
            sizes.append(float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0))))
        if sizes:
            max_size = max(sizes)
            if max_size < 0.1:
                return "microscopic"
            if max_size < 1.0:
                return "object"
            if max_size < 5.0:
                return "furniture"
            if max_size < 20.0:
                return "room"
            if max_size < 100.0:
                return "building"
            if max_size < 1000.0:
                return "campus"
            return "city"
    return "room"


def _infer_camera_profile(navigation_mode: str) -> str:
    return {
        "WALK": "first_person",
        "EXAMINE": "inspection",
        "FLY": "drone",
        "LOOKAT": "presentation",
        "ANY": "presentation",
        "NONE": "cinematic",
    }.get(navigation_mode, "first_person")


def _infer_perspective_type() -> str:
    """Default to a human embodiment unless additional scene semantics are available."""
    return "HumanPerspective"


def build_perspective_model(scene: Any, viewpoint: str | None = None, renderer: str = "spec") -> PerspectiveModel:
    """Create a schema-shaped perspective model from a runtime scene."""
    p = perspective.from_viewpoint(scene, viewpoint, renderer)
    view_names = [v.name for v in getattr(scene, "viewpoints", []) or []]
    if not view_names:
        view_names = [p.viewpoint]

    navigation_mode = p.navigation_mode or "WALK"
    scale_class = _infer_scale_class(scene)
    coordinate_frame = _default_coordinate_frame()
    affordances = ["WalkableRegion", "ObservationPoint"]
    if "Entrance" in view_names or "Entry" in view_names:
        affordances.append("Entrance")
    if "Exit" in view_names or "Exit" in view_names:
        affordances.append("Exit")
    if not affordances:
        affordances = ["ObservationPoint"]

    observer_properties = {
        "standing_height_m": 1.75,
        "eye_height_m": float(getattr(p, "eye_height", 1.6)),
        "navigation_type": list(getattr(p, "navigation_type", [])),
        "support": getattr(p, "support", None),
        "falls": bool(getattr(p, "falls", False)),
        "renderer": renderer,
    }

    accessibility_features = [
        "wheelchair_navigation",
        "alternative_navigation",
        "low_vision_support",
        "reduced_motion",
    ]

    return PerspectiveModel(
        perspective_type=_infer_perspective_type(),
        coordinate_frame=coordinate_frame,
        scale_class=scale_class,
        navigation_mode=navigation_mode,
        camera_profile=_infer_camera_profile(navigation_mode),
        observer_properties=observer_properties,
        viewpoints=view_names,
        affordances=affordances,
        accessibility_features=accessibility_features,
        notes=list(getattr(p, "notes", [])),
    )


def validate_perspective_model(model: Any) -> list[str]:
    """Return validation errors for a perspective model object.

    This is intentionally lightweight and checks the minimal contract required by the
    proposed skill schema: reference frame, observer model, scale, navigation, viewpoints,
    affordances, and accessibility.
    """
    errors: list[str] = []

    if not getattr(model, "perspective_type", "").strip():
        errors.append("perspective_type is required")
    if getattr(model, "coordinate_frame", None) is None:
        errors.append("coordinate_frame is required")
    elif getattr(model.coordinate_frame, "handedness", "").strip() not in {"right", "left"}:
        errors.append("coordinate_frame.handedness must be 'right' or 'left'")
    if not getattr(model, "scale_class", "").strip():
        errors.append("scale_class is required")
    if not getattr(model, "navigation_mode", "").strip():
        errors.append("navigation_mode is required")
    if not getattr(model, "camera_profile", "").strip():
        errors.append("camera_profile is required")
    if not getattr(model, "observer_properties", None):
        errors.append("observer_properties is required")
    if not getattr(model, "viewpoints", None):
        errors.append("viewpoints is required")
    if not getattr(model, "affordances", None):
        errors.append("affordances is required")
    if getattr(model, "accessibility_features", None) is None:
        errors.append("accessibility_features is required")

    return errors
