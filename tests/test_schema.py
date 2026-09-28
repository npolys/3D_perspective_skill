import pytest

from x3d_perspective import (
    build_decision_trace,
    build_environment_rule_table,
    build_integration_contract,
    build_observer_profile_contract,
    build_perspective_model,
    build_skill_contract,
    build_taxonomy_contract,
    validate_perspective_model,
)
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


def test_validate_perspective_model_rejects_invalid_semantic_contract():
    scene = x3d_loader.load(ROOM)
    model = build_perspective_model(scene, viewpoint="Entry", renderer="spec")
    model.semantic_inputs = type("S", (), {
        "scene_purpose": "",
        "target_users": [],
        "locomotion_type": "INVALID",
        "environment_type": "",
        "interaction_type": "",
        "scale_requirements": [],
        "accessibility_requirements": [],
    })()

    errors = validate_perspective_model(model)
    assert any("semantic_inputs" in e.lower() for e in errors)
    assert any("locomotion_type" in e.lower() for e in errors)


def test_validate_perspective_model_rejects_taxonomy_mismatch():
    scene = x3d_loader.load(ROOM)
    model = build_perspective_model(scene, viewpoint="Entry", renderer="spec")
    model.perspective_type = "DronePerspective"
    model.navigation_mode = "WALK"
    model.camera_profile = "first_person"

    errors = validate_perspective_model(model)
    assert any("drone" in e.lower() or "navigation_mode" in e.lower() for e in errors)


def test_build_skill_contract_exposes_literal_schema_fields():
    contract = build_skill_contract()

    assert contract.skill_name == "ISO-X3D-Perspective-Architect"
    assert contract.dependencies
    assert contract.outputs
    assert contract.principles
    assert contract.validation
    assert contract.contract


def test_build_taxonomy_contract_exposes_explicit_taxonomy():
    taxonomy = build_taxonomy_contract()

    assert taxonomy["perspective_types"]
    assert "HumanPerspective" in taxonomy["perspective_types"]
    assert "DronePerspective" in taxonomy["perspective_types"]
    assert taxonomy["observer_profile"]["eye_height_m"] > 0
    assert taxonomy["viewpoint_types"]


def test_build_environment_rule_table_maps_scene_context_to_navigation():
    rules = build_environment_rule_table()

    assert rules["museum"]["navigation_mode"] == "WALK"
    assert rules["city"]["navigation_mode"] == "WALK"
    assert rules["terrain"]["navigation_mode"] == "FLY"
    assert rules["molecular"]["navigation_mode"] == "EXAMINE"


def test_build_observer_profile_contract_exposes_default_human_profile():
    profile = build_observer_profile_contract()

    assert profile["standing_height_m"] == 1.75
    assert profile["eye_height_m"] == 1.6
    assert profile["collision_radius_m"] > 0
    assert "wheelchair" in profile["supports"]


def test_build_decision_trace_exposes_reasoned_schema_output():
    trace = build_decision_trace(model_type="HumanPerspective", navigation_mode="WALK", scene_context="museum")

    assert trace["decision"] == "WALK"
    assert trace["reason"]
    assert trace["scene_context"] == "museum"
    assert trace["camera_profile"]


def test_build_integration_contract_exposes_pipeline_flow():
    contract = build_integration_contract()

    assert contract["pipeline"][0] == "ontology_reasoning"
    assert contract["pipeline"][-1] == "downstream_authoring"
    assert contract["outputs"]["perspective_model"]
    assert contract["outputs"]["decision_trace"]
