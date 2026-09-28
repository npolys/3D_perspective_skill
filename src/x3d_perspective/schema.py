"""Formal schema-shaped output for the perspective skill contract.

This layer bridges the runtime perspective engine with the proposed skill schema by
exposing a compact typed model that can be validated and handed downstream to later
X3D authoring stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from . import perspective


class PerspectiveType(str, Enum):
    HUMAN = "HumanPerspective"
    CHILD = "ChildPerspective"
    WHEELCHAIR = "WheelchairPerspective"
    SEATED = "SeatedPerspective"
    VEHICLE = "VehiclePerspective"
    DRONE = "DronePerspective"
    ROBOT = "RobotPerspective"
    ARCHITECTURAL = "ArchitecturalPerspective"
    PLANETARY = "PlanetaryPerspective"
    GEOSPATIAL = "GeospatialPerspective"
    MICROSCOPIC = "MicroscopicPerspective"
    MOLECULAR = "MolecularPerspective"
    ASTRONOMICAL = "AstronomicalPerspective"
    DATA_VISUALIZATION = "DataVisualizationPerspective"


class ScaleClass(str, Enum):
    MICROSCOPIC = "microscopic"
    OBJECT = "object"
    FURNITURE = "furniture"
    ROOM = "room"
    BUILDING = "building"
    CAMPUS = "campus"
    CITY = "city"
    REGIONAL = "regional"
    PLANETARY = "planetary"
    ASTRONOMICAL = "astronomical"


class NavigationMode(str, Enum):
    WALK = "WALK"
    FLY = "FLY"
    EXAMINE = "EXAMINE"
    LOOKAT = "LOOKAT"
    ANY = "ANY"
    NONE = "NONE"


class CameraProfile(str, Enum):
    FIRST_PERSON = "first_person"
    INSPECTION = "inspection"
    CINEMATIC = "cinematic"
    ORTHOGRAPHIC = "orthographic"
    DRONE = "drone"
    GEOSPATIAL = "geospatial"
    PRESENTATION = "presentation"


class Affordance(str, Enum):
    WALKABLE_REGION = "WalkableRegion"
    OBSERVATION_POINT = "ObservationPoint"
    ENTRANCE = "Entrance"
    EXIT = "Exit"
    PORTAL = "Portal"
    OBSTACLE = "Obstacle"
    DESTINATION = "Destination"
    WORKSPACE = "Workspace"
    GATHERING_AREA = "GatheringArea"


class AccessibilityFeature(str, Enum):
    WHEELCHAIR_NAVIGATION = "wheelchair_navigation"
    SEATED_VIEWPOINTS = "seated_viewpoints"
    LOW_VISION_SUPPORT = "low_vision_support"
    ALTERNATIVE_NAVIGATION = "alternative_navigation"
    REDUCED_MOTION = "reduced_motion"


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

    def as_dict(self) -> dict[str, Any]:
        return {
            "handedness": self.handedness,
            "up_axis": self.up_axis,
            "right_axis": self.right_axis,
            "forward_axis": self.forward_axis,
            "gravity_axis": self.gravity_axis,
            "supports": list(self.supports),
        }


@dataclass
class SemanticInputs:
    scene_purpose: str = "general_exploration"
    target_users: list[str] = field(default_factory=lambda: ["adult_users"])
    locomotion_type: str = "WALK"
    environment_type: str = "indoor"
    interaction_type: str = "inspection"
    scale_requirements: list[str] = field(default_factory=lambda: ["human_scale"])
    accessibility_requirements: list[str] = field(default_factory=lambda: ["standard_access"])

    def as_dict(self) -> dict[str, Any]:
        return {
            "scene_purpose": self.scene_purpose,
            "target_users": list(self.target_users),
            "locomotion_type": self.locomotion_type,
            "environment_type": self.environment_type,
            "interaction_type": self.interaction_type,
            "scale_requirements": list(self.scale_requirements),
            "accessibility_requirements": list(self.accessibility_requirements),
        }


@dataclass
class PerspectiveModel:
    perspective_type: PerspectiveType | str
    coordinate_frame: CoordinateFrame
    scale_class: ScaleClass | str
    navigation_mode: NavigationMode | str
    camera_profile: CameraProfile | str
    observer_properties: dict[str, Any]
    semantic_inputs: SemanticInputs
    viewpoints: list[str]
    affordances: list[Affordance | str]
    accessibility_features: list[AccessibilityFeature | str] | None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "perspective_type": self._value(self.perspective_type),
            "coordinate_frame": self.coordinate_frame.as_dict(),
            "scale_class": self._value(self.scale_class),
            "navigation_mode": self._value(self.navigation_mode),
            "camera_profile": self._value(self.camera_profile),
            "observer_properties": self.observer_properties,
            "semantic_inputs": self.semantic_inputs.as_dict(),
            "viewpoints": list(self.viewpoints),
            "affordances": [self._value(v) for v in self.affordances],
            "accessibility_features": [self._value(v) for v in (self.accessibility_features or [])],
            "notes": list(self.notes),
        }

    @staticmethod
    def _value(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        return value


@dataclass
class SkillContract:
    skill_name: str = "ISO-X3D-Perspective-Architect"
    description: str = (
        "Reason from the active viewer's perspective before scene generation, using X3D viewpoint, "
        "navigation, coordinate-frame, and accessibility semantics to generate a valid perspective model."
    )
    dependencies: list[str] = field(
        default_factory=lambda: [
            "x3d_perspective.perspective",
            "x3d_perspective.frames",
            "x3d_perspective.view",
            "x3d_perspective.relations",
            "x3d_perspective.x3d_loader",
        ]
    )
    outputs: list[str] = field(
        default_factory=lambda: [
            "PerspectiveModel",
            "SemanticInputs",
            "coordinate_frame",
            "scale_class",
            "navigation_mode",
            "camera_profile",
            "affordances",
            "accessibility_features",
        ]
    )
    principles: list[str] = field(
        default_factory=lambda: [
            "geometry_follows_experience",
            "viewpoint_before_modeling",
            "scale_before_geometry",
            "navigation_before_interaction",
            "embodiment_before_camera",
        ]
    )
    validation: dict[str, list[str]] = field(
        default_factory=lambda: {
            "required_fields": [
                "perspective_type",
                "coordinate_frame",
                "scale_class",
                "navigation_mode",
                "camera_profile",
                "observer_properties",
                "semantic_inputs",
                "viewpoints",
                "affordances",
                "accessibility_features",
            ],
            "consistency_rules": [
                "DronePerspective requires aerial navigation_mode",
                "GeospatialPerspective and PlanetaryPerspective are not compatible with WALK",
                "semantic_inputs.locomotion_type must be one of WALK, FLY, EXAMINE, LOOKAT, ANY, NONE",
            ],
        }
    )
    contract: dict[str, Any] = field(
        default_factory=lambda: {
            "perspective_type": "HumanPerspective",
            "coordinate_frame": CoordinateFrame().as_dict(),
            "scale_class": "room",
            "navigation_mode": "WALK",
            "camera_profile": "first_person",
            "semantic_inputs": SemanticInputs().as_dict(),
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "description": self.description,
            "dependencies": list(self.dependencies),
            "outputs": list(self.outputs),
            "principles": list(self.principles),
            "validation": {k: list(v) for k, v in self.validation.items()},
            "contract": self.contract,
        }


def build_taxonomy_contract() -> dict[str, Any]:
    """Return the explicit taxonomy and default observer profile used by the skill contract."""
    return {
        "perspective_types": [
            "HumanPerspective",
            "ChildPerspective",
            "WheelchairPerspective",
            "SeatedPerspective",
            "VehiclePerspective",
            "DronePerspective",
            "RobotPerspective",
            "ArchitecturalPerspective",
            "PlanetaryPerspective",
            "GeospatialPerspective",
            "MicroscopicPerspective",
            "MolecularPerspective",
            "AstronomicalPerspective",
            "DataVisualizationPerspective",
        ],
        "viewpoint_types": [
            "EntranceView",
            "OverviewView",
            "InspectionView",
            "NavigationView",
            "PresentationView",
        ],
        "observer_profile": {
            "standing_height_m": 1.75,
            "eye_height_m": 1.6,
            "shoulder_width_m": 0.45,
            "collision_radius_m": 0.35,
            "step_height_m": 0.15,
            "supports": ["standing", "seated", "wheelchair"],
        },
    }


def build_environment_rule_table() -> dict[str, dict[str, str | list[str]]]:
    """Return environment-to-navigation and camera rules used by the schema contract."""
    return {
        "museum": {
            "navigation_mode": "WALK",
            "camera_profile": "inspection",
            "scene_purpose": "museum_exploration",
            "interaction_type": "inspection",
        },
        "city": {
            "navigation_mode": "WALK",
            "camera_profile": "geospatial",
            "scene_purpose": "wayfinding_and_navigation",
            "interaction_type": "arrival_and_navigation",
        },
        "terrain": {
            "navigation_mode": "FLY",
            "camera_profile": "drone",
            "scene_purpose": "wayfinding_and_navigation",
            "interaction_type": "overview_and_context",
        },
        "molecular": {
            "navigation_mode": "EXAMINE",
            "camera_profile": "inspection",
            "scene_purpose": "microscopic_observation",
            "interaction_type": "inspection",
        },
        "indoor": {
            "navigation_mode": "WALK",
            "camera_profile": "first_person",
            "scene_purpose": "general_exploration",
            "interaction_type": "inspection",
        },
        "outdoor": {
            "navigation_mode": "WALK",
            "camera_profile": "presentation",
            "scene_purpose": "general_exploration",
            "interaction_type": "overview_and_context",
        },
    }


def build_observer_profile_contract() -> dict[str, Any]:
    """Return the default adult human observer profile used by the skill schema."""
    return {
        "standing_height_m": 1.75,
        "eye_height_m": 1.60,
        "shoulder_width_m": 0.45,
        "collision_radius_m": 0.35,
        "step_height_m": 0.15,
        "body_mass_kg": 70.0,
        "supports": ["standing", "seated", "wheelchair"],
        "navigation_preferences": ["WALK", "LOOKAT", "EXAMINE"],
    }


def build_decision_trace(
    model_type: str,
    navigation_mode: str,
    scene_context: str,
    camera_profile: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Return a schema-shaped decision trace for explainability and downstream authoring."""
    effective_camera = camera_profile or {
        "WALK": "first_person",
        "FLY": "drone",
        "EXAMINE": "inspection",
        "LOOKAT": "presentation",
    }.get(str(navigation_mode).upper(), "presentation")
    effective_reason = reason or (
        "The active scene context and navigation semantics support the selected motion profile and camera framing."
    )

    return {
        "decision": str(navigation_mode).upper(),
        "model_type": str(model_type),
        "scene_context": str(scene_context),
        "camera_profile": str(effective_camera),
        "reason": effective_reason,
        "evidence": [
            "scene_context_match",
            "navigation_mode_consistency",
            "camera_profile_consistency",
            "accessibility_compatibility",
        ],
    }


def build_integration_contract() -> dict[str, Any]:
    """Return the end-to-end pipeline contract connecting schema inference to downstream authoring."""
    return {
        "pipeline": [
            "ontology_reasoning",
            "scene_context_inference",
            "taxonomy_selection",
            "semantic_validation",
            "perspective_model_build",
            "decision_trace",
            "downstream_authoring",
        ],
        "inputs": {
            "scene": "X3D scene object or scene graph",
            "viewpoint": "Selected viewpoint identifier",
            "renderer": "Rendering mode or renderer label",
        },
        "outputs": {
            "perspective_model": "PerspectiveModel data object",
            "semantic_inputs": "semantic input classification",
            "decision_trace": "structured decision explanation",
            "authoring_plan": "downstream geometry or interaction plan",
        },
        "contract": {
            "preconditions": [
                "Scene must provide viewpoint and transform context",
                "Navigation mode should be compatible with perspective type",
                "Semantic inputs should be populated before downstream authoring",
            ],
            "postconditions": [
                "Perspective model is valid against schema rules",
                "Decision trace is available for explainability",
                "Scene authoring can consume the perspective contract safely",
            ],
        },
    }


DEFAULT_COORDINATE_FRAME = CoordinateFrame()


def _normalize_enum(value: Any, enum_cls: type[Enum], default: Enum) -> Enum:
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    normalized = str(value).strip()
    for member in enum_cls:
        if normalized == member.value:
            return member
    return default


def _default_coordinate_frame() -> CoordinateFrame:
    return DEFAULT_COORDINATE_FRAME


def _infer_scale_class(scene: Any) -> ScaleClass:
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
                return ScaleClass.MICROSCOPIC
            if max_size < 1.0:
                return ScaleClass.OBJECT
            if max_size < 5.0:
                return ScaleClass.FURNITURE
            if max_size < 20.0:
                return ScaleClass.ROOM
            if max_size < 100.0:
                return ScaleClass.BUILDING
            if max_size < 1000.0:
                return ScaleClass.CAMPUS
            return ScaleClass.CITY
    return ScaleClass.ROOM


def _infer_camera_profile(navigation_mode: NavigationMode | str) -> CameraProfile:
    mode = _normalize_enum(navigation_mode, NavigationMode, NavigationMode.WALK)
    return {
        NavigationMode.WALK: CameraProfile.FIRST_PERSON,
        NavigationMode.EXAMINE: CameraProfile.INSPECTION,
        NavigationMode.FLY: CameraProfile.DRONE,
        NavigationMode.LOOKAT: CameraProfile.PRESENTATION,
        NavigationMode.ANY: CameraProfile.PRESENTATION,
        NavigationMode.NONE: CameraProfile.CINEMATIC,
    }.get(mode, CameraProfile.FIRST_PERSON)


def infer_semantic_inputs(scene: Any, viewpoint: str | None = None, renderer: str = "spec") -> SemanticInputs:
    """Infer the schema's semantic input contract from runtime scene context and navigation state."""
    p = perspective.from_viewpoint(scene, viewpoint, renderer)
    view_names = [v.name for v in getattr(scene, "viewpoints", []) or []]
    scene_name = getattr(scene, "path", "")
    path_text = str(scene_name).lower()

    if any(token in path_text for token in ("geospatial", "terrain", "planet", "earth", "city", "campus")):
        environment_type = "outdoor"
    elif any(token in path_text for token in ("room", "museum", "interior", "building")):
        environment_type = "indoor"
    else:
        environment_type = "indoor"

    navigation_type = str((getattr(p, "navigation_type", []) or ["WALK"])[0]).upper()
    locomotion_type = navigation_type if navigation_type in {"WALK", "FLY", "EXAMINE", "LOOKAT"} else "WALK"

    if any(token in path_text for token in ("molecule", "microscope", "cell", "protein")):
        scene_purpose = "microscopic_observation"
    elif any(token in path_text for token in ("museum", "gallery", "exhibit")):
        scene_purpose = "museum_exploration"
    elif any(token in path_text for token in ("city", "street", "terrain", "landscape")):
        scene_purpose = "wayfinding_and_navigation"
    else:
        scene_purpose = "general_exploration"

    if "Entry" in view_names or "Entrance" in view_names:
        interaction_type = "arrival_and_navigation"
    elif any(token in view_names for token in ("Overlook", "Overview", "Bird")):
        interaction_type = "overview_and_context"
    else:
        interaction_type = "inspection"

    scale_requirements = [str(_infer_scale_class(scene).value)]
    accessibility_requirements = ["standard_access"]

    return SemanticInputs(
        scene_purpose=scene_purpose,
        target_users=["adult_users"],
        locomotion_type=locomotion_type,
        environment_type=environment_type,
        interaction_type=interaction_type,
        scale_requirements=scale_requirements,
        accessibility_requirements=accessibility_requirements,
    )


def _infer_perspective_type(scene: Any) -> PerspectiveType:
    """Default to a human embodiment unless additional scene semantics suggest a more specific perspective."""
    path_text = str(getattr(scene, "path", "")).lower()
    if any(token in path_text for token in ("drone", "flight", "aircraft", "terrain")):
        return PerspectiveType.DRONE
    if any(token in path_text for token in ("planet", "earth", "moon", "orbit", "solar")):
        return PerspectiveType.PLANETARY
    if any(token in path_text for token in ("molecule", "micro", "cell", "protein")):
        return PerspectiveType.MOLECULAR
    if any(token in path_text for token in ("city", "campus", "geospatial")):
        return PerspectiveType.GEOSPATIAL
    return PerspectiveType.HUMAN


def build_skill_contract() -> SkillContract:
    """Return the explicit machine-readable contract for the perspective skill."""
    return SkillContract()


def build_perspective_model(scene: Any, viewpoint: str | None = None, renderer: str = "spec") -> PerspectiveModel:
    """Create a schema-shaped perspective model from a runtime scene."""
    p = perspective.from_viewpoint(scene, viewpoint, renderer)
    view_names = [v.name for v in getattr(scene, "viewpoints", []) or []]
    if not view_names:
        view_names = [p.viewpoint]

    navigation_mode = _normalize_enum(p.navigation_mode or "WALK", NavigationMode, NavigationMode.WALK)
    scale_class = _infer_scale_class(scene)
    coordinate_frame = _default_coordinate_frame()
    semantic_inputs = infer_semantic_inputs(scene, viewpoint, renderer)
    affordances = [Affordance.WALKABLE_REGION, Affordance.OBSERVATION_POINT]
    if "Entrance" in view_names or "Entry" in view_names:
        affordances.append(Affordance.ENTRANCE)
    if "Exit" in view_names or "Exit" in view_names:
        affordances.append(Affordance.EXIT)
    if not affordances:
        affordances = [Affordance.OBSERVATION_POINT]

    observer_properties = {
        "standing_height_m": 1.75,
        "eye_height_m": float(getattr(p, "eye_height", 1.6)),
        "navigation_type": list(getattr(p, "navigation_type", [])),
        "support": getattr(p, "support", None),
        "falls": bool(getattr(p, "falls", False)),
        "renderer": renderer,
        "semantic_inputs": semantic_inputs.as_dict(),
    }

    accessibility_features = [
        AccessibilityFeature.WHEELCHAIR_NAVIGATION,
        AccessibilityFeature.ALTERNATIVE_NAVIGATION,
        AccessibilityFeature.LOW_VISION_SUPPORT,
        AccessibilityFeature.REDUCED_MOTION,
    ]

    return PerspectiveModel(
        perspective_type=_infer_perspective_type(scene),
        coordinate_frame=coordinate_frame,
        scale_class=scale_class,
        navigation_mode=navigation_mode,
        camera_profile=_infer_camera_profile(navigation_mode),
        observer_properties=observer_properties,
        semantic_inputs=semantic_inputs,
        viewpoints=view_names,
        affordances=affordances,
        accessibility_features=accessibility_features,
        notes=list(getattr(p, "notes", [])),
    )


def _validate_semantic_input_contract(model: Any, errors: list[str]) -> None:
    semantic_inputs = getattr(model, "semantic_inputs", None)
    if semantic_inputs is None:
        errors.append("semantic_inputs is required")
        return

    valid_locomotion = {"WALK", "FLY", "EXAMINE", "LOOKAT", "ANY", "NONE"}
    valid_env_types = {"indoor", "outdoor", "mixed", "micro", "planetary", "geospatial"}
    valid_interactions = {
        "inspection",
        "overview_and_context",
        "arrival_and_navigation",
        "wayfinding",
        "navigation",
        "general_exploration",
    }

    if not getattr(semantic_inputs, "scene_purpose", "").strip():
        errors.append("semantic_inputs.scene_purpose is required")
    if not getattr(semantic_inputs, "target_users", None):
        errors.append("semantic_inputs.target_users is required")
    locomotion_type = str(getattr(semantic_inputs, "locomotion_type", "")).upper()
    if locomotion_type not in valid_locomotion:
        errors.append(
            "semantic_inputs.locomotion_type must be one of: " + ", ".join(sorted(valid_locomotion))
        )
    if str(getattr(semantic_inputs, "environment_type", "")).lower() not in valid_env_types:
        errors.append(
            "semantic_inputs.environment_type must be one of: " + ", ".join(sorted(valid_env_types))
        )
    if str(getattr(semantic_inputs, "interaction_type", "")).lower() not in valid_interactions:
        errors.append(
            "semantic_inputs.interaction_type must be one of: " + ", ".join(sorted(valid_interactions))
        )
    if not getattr(semantic_inputs, "scale_requirements", None):
        errors.append("semantic_inputs.scale_requirements is required")
    if not getattr(semantic_inputs, "accessibility_requirements", None):
        errors.append("semantic_inputs.accessibility_requirements is required")


def _normalize_model_value(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value or "").strip()


def _validate_taxonomy_consistency(model: Any, errors: list[str]) -> None:
    perspective_type = _normalize_model_value(getattr(model, "perspective_type", ""))
    navigation_mode = _normalize_model_value(getattr(model, "navigation_mode", ""))
    camera_profile = _normalize_model_value(getattr(model, "camera_profile", ""))

    perspective_name = perspective_type.lower()
    nav_name = navigation_mode.upper()
    camera_name = camera_profile.lower()

    if "drone" in perspective_name and nav_name in {"WALK", "EXAMINE"}:
        errors.append("DronePerspective requires a flying or aerial navigation_mode, not WALK/EXAMINE")
    if "drone" in perspective_name and camera_name not in {"drone", "presentation", "cinematic"}:
        errors.append("DronePerspective requires a drone-oriented camera_profile")
    if perspective_name in {"geospatialperspective", "planetaryperspective"} and nav_name == "WALK":
        errors.append("GeospatialPerspective and PlanetaryPerspective are not compatible with WALK navigation_mode")


def validate_perspective_model(model: Any) -> list[str]:
    """Return validation errors for a perspective model object.

    This checks the minimal contract required by the proposed skill schema: reference
    frame, observer model, scale, navigation, viewpoints, affordances, accessibility,
    and the semantic-input contract used to classify the scene.
    """
    errors: list[str] = []

    perspective_type = getattr(model, "perspective_type", None)
    if perspective_type is None or str(perspective_type).strip() == "":
        errors.append("perspective_type is required")

    if getattr(model, "coordinate_frame", None) is None:
        errors.append("coordinate_frame is required")
    elif getattr(model.coordinate_frame, "handedness", "").strip() not in {"right", "left"}:
        errors.append("coordinate_frame.handedness must be 'right' or 'left'")

    if getattr(model, "scale_class", None) is None or str(model.scale_class).strip() == "":
        errors.append("scale_class is required")
    if getattr(model, "navigation_mode", None) is None or str(model.navigation_mode).strip() == "":
        errors.append("navigation_mode is required")
    if getattr(model, "camera_profile", None) is None or str(model.camera_profile).strip() == "":
        errors.append("camera_profile is required")
    if not getattr(model, "observer_properties", None):
        errors.append("observer_properties is required")
    _validate_semantic_input_contract(model, errors)
    _validate_taxonomy_consistency(model, errors)
    if not getattr(model, "viewpoints", None):
        errors.append("viewpoints is required")
    if not getattr(model, "affordances", None):
        errors.append("affordances is required")
    if getattr(model, "accessibility_features", None) is None:
        errors.append("accessibility_features is required")

    return errors
