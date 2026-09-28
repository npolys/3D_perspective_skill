import pytest

from x3d_perspective import build_perspective_model, validate_perspective_model
from x3d_perspective import x3d_loader
from conftest import ROOM


def test_build_perspective_model_matches_contract():
    scene = x3d_loader.load(ROOM)
    model = build_perspective_model(scene, viewpoint="Entry", renderer="spec")

    assert model.perspective_type == "HumanPerspective"
    assert model.coordinate_frame.handedness == "right"
    assert model.coordinate_frame.up_axis == "+Y"
    assert model.scale_class in {"room", "building", "campus", "city", "object", "furniture"}
    assert model.navigation_mode in {"WALK", "EXAMINE", "FLY", "LOOKAT", "ANY", "NONE"}
    assert model.camera_profile in {"first_person", "inspection", "cinematic", "orthographic", "drone", "geospatial", "presentation"}
    assert model.viewpoints
    assert model.affordances
    assert model.accessibility_features is not None

    errors = validate_perspective_model(model)
    assert errors == []


def test_validate_perspective_model_detects_missing_required_values():
    model = type("M", (), {
        "perspective_type": "",
        "coordinate_frame": None,
        "scale_class": "",
        "navigation_mode": "",
        "camera_profile": "",
        "observer_properties": {},
        "viewpoints": [],
        "affordances": [],
        "accessibility_features": None,
    })()

    assert validate_perspective_model(model)
