# ISO-X3D-Perspective-Architect Compliance Matrix

This document records how the current repository implementation matches the proposed agentic skill schema for “ISO-X3D-Perspective-Architect” as implemented in the current codebase.

The matrix distinguishes between:

- ✅ Implemented and validated
- ⚠️ Partially implemented or intentionally runtime-oriented
- ❌ Not a formal repo artifact (not yet represented as a first-class project file)

## 1) Vision and intent

- [x] The repo is explicitly about reasoning from the observer's perspective before scene generation.
  - Evidence: [README.md](README.md), [SKILL.md](SKILL.md), [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] The package models the effective camera from the bound `Viewpoint` and `NavigationInfo`.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] The project treats perspective as a semantic foundation for downstream spatial reasoning.
  - Evidence: [README.md](README.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 2) Skill metadata and schema structure

- [x] The repository has a skill description and usage contract in the agent-facing docs.
  - Evidence: [SKILL.md](SKILL.md)
- [x] The package exposes a runtime perspective API and a formal schema layer.
  - Evidence: [src/x3d_perspective/__init__.py](src/x3d_perspective/__init__.py), [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)
- [x] The repo now includes a machine-readable skill contract object.
  - Evidence: `build_skill_contract()`, `SkillContract`, [tests/test_schema.py](tests/test_schema.py)
- [x] The repo includes explicit validation and contract builders for taxonomy, environment mapping, observer profile, decision trace, and integration chain.
  - Evidence: [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 3) Core principles

- [x] `geometry_follows_experience`: implemented as a core runtime principle.
  - Evidence: [README.md](README.md), [src/x3d_perspective/view.py](src/x3d_perspective/view.py)
- [x] `viewpoint_before_modeling`: implemented.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] `scale_before_geometry`: implemented.
  - Evidence: [src/x3d_perspective/frames.py](src/x3d_perspective/frames.py)
- [x] `navigation_before_interaction`: implemented.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] `embodiment_before_camera`: implemented.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)

## 4) Coordinate systems

- [x] The runtime system models up, gravity, and the viewer's frame.
  - Evidence: [src/x3d_perspective/frames.py](src/x3d_perspective/frames.py)
- [x] The default coordinate convention is right-handed, Y-up, with gravity along -Y.
  - Evidence: [src/x3d_perspective/frames.py](src/x3d_perspective/frames.py), [tests/test_frame.py](tests/test_frame.py)
- [x] Local coordinate frames, transforms, and nested scene structure are accounted for.
  - Evidence: [src/x3d_perspective/x3d_loader.py](src/x3d_perspective/x3d_loader.py)
- [x] A formal coordinate-frame data structure is included in the schema layer.
  - Evidence: `CoordinateFrame` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 5) Units and measures

- [x] Scene units are converted to meters and reported.
  - Evidence: [src/x3d_perspective/frames.py](src/x3d_perspective/frames.py), [docs/API.md](docs/API.md)
- [x] Lengths and body dimensions are expressed in meter-based terms.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] The package reasons over human scale, body scale, and image scale.
  - Evidence: [README.md](README.md), [src/x3d_perspective/view.py](src/x3d_perspective/view.py)

## 6) Human factors and observer model

- [x] The code models eye height, collision radius, step height, and navigation body assumptions.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] Body assumptions inform the effective camera placement under WALK.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] The default adult human profile is represented in the schema layer.
  - Evidence: `build_observer_profile_contract()` and `build_taxonomy_contract()` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 7) Observer ontology and perspective taxonomy

- [x] The repo includes a formal perspective taxonomy in the schema layer.
  - Evidence: `PerspectiveType`, `CameraProfile`, `NavigationMode`, `ScaleClass`, and `build_taxonomy_contract()` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)
- [x] Enumerations such as `HumanPerspective`, `DronePerspective`, `GeospatialPerspective`, and others are explicitly represented.
  - Evidence: [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)
- [x] The runtime engine's operational semantics align with the taxonomy.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)

## 8) Semantic input contract

- [x] The repo includes a formal `SemanticInputs` object.
  - Evidence: [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)
- [x] It includes `scene_purpose`, `target_users`, `locomotion_type`, `environment_type`, `interaction_type`, `scale_requirements`, and `accessibility_requirements`.
  - Evidence: `SemanticInputs` and `infer_semantic_inputs()` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)
- [x] Validation rejects invalid semantic contracts.
  - Evidence: `validate_perspective_model()` and [tests/test_schema.py](tests/test_schema.py)

## 9) Context and environment inference

- [x] Contextual scene reasoning is implemented in the runtime engine and schema layer.
  - Evidence: `infer_semantic_inputs()` and `build_environment_rule_table()` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)
- [x] The repo includes an explicit environment-rule table for contexts such as museum, city, terrain, molecular, indoor, and outdoor.
  - Evidence: [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py), [tests/test_schema.py](tests/test_schema.py)

## 10) Scale reasoning and scale classes

- [x] The repo infers scene scale and converts to meters.
  - Evidence: [src/x3d_perspective/frames.py](src/x3d_perspective/frames.py)
- [x] The schema includes explicit scale-class enums: `microscopic`, `object`, `furniture`, `room`, `building`, `campus`, `city`, etc.
  - Evidence: `ScaleClass` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)
- [x] The runtime and schema both normalize units and body scales before geometry reasoning.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py), [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 11) Viewpoint synthesis

- [x] The code extracts and summarizes a scene's `Viewpoint`s.
  - Evidence: [src/x3d_perspective/x3d_loader.py](src/x3d_perspective/x3d_loader.py)
- [x] The runtime model represents the currently active viewpoint and its effective pose.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] The schema lists viewpoint-related classifications and exposes them within the perspective model.
  - Evidence: `viewpoints` in `PerspectiveModel` and `build_taxonomy_contract()` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 12) Camera reasoning

- [x] Camera projection, near/far values, FOV, and viewport effects are implemented.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py), [src/x3d_perspective/view.py](src/x3d_perspective/view.py)
- [x] The package models rectangular FOV and image-space projection.
  - Evidence: [src/x3d_perspective/view.py](src/x3d_perspective/view.py)
- [x] It distinguishes camera profiles by navigation mode.
  - Evidence: `CameraProfile` and `_infer_camera_profile()` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 13) Navigation reasoning

- [x] `WALK`, `FLY`, `EXAMINE`, and `LOOKAT` are implemented in practice.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] The runtime logic distinguishes authored pose from grounded runtime behavior.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] Environment-to-navigation rules are formalized in the schema layer.
  - Evidence: `build_environment_rule_table()` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 14) Scenegraph semantics and relations

- [x] Spatial relations including support, visibility, above/below, front/back, and viewer-relative placement are implemented.
  - Evidence: [src/x3d_perspective/relations.py](src/x3d_perspective/relations.py), [src/x3d_perspective/view.py](src/x3d_perspective/view.py)
- [x] Scene structure and object relationships are available as analysis outputs.
  - Evidence: [src/x3d_perspective/x3d_loader.py](src/x3d_perspective/x3d_loader.py)
- [x] The schema layer exposes affordance and accessibility outputs usable for downstream reasoning.
  - Evidence: `Affordance`, `AccessibilityFeature`, `PerspectiveModel` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 15) Affordance model

- [x] The repo infers operational affordances from the scene and view.
  - Evidence: [src/x3d_perspective/relations.py](src/x3d_perspective/relations.py), [src/x3d_perspective/view.py](src/x3d_perspective/view.py)
- [x] The schema layer includes a formal affordance enum set.
  - Evidence: `Affordance` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 16) Accessibility reasoning

- [x] Accessibility-related factors are represented in the schema model.
  - Evidence: `AccessibilityFeature` and `accessibility_features` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)
- [x] The repo includes explicit accessibility features such as wheelchair support, alternative navigation, low-vision support, and reduced motion.
  - Evidence: [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 17) Generated output model and formal contract

- [x] A schema-shaped output layer is present in the repo and exported from the package.
  - Evidence: [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py), [src/x3d_perspective/__init__.py](src/x3d_perspective/__init__.py)
- [x] The model includes the key required sections: perspective type, coordinate frame, scale class, navigation mode, camera profile, observer properties, viewpoints, affordances, and accessibility features.
  - Evidence: `PerspectiveModel` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)
- [x] The repo validates the model against required fields and taxonomy rules.
  - Evidence: `validate_perspective_model()` and [tests/test_schema.py](tests/test_schema.py)

## 18) Explainability

- [x] The implementation records notes and reasons for chosen navigation and camera behavior.
  - Evidence: [src/x3d_perspective/perspective.py](src/x3d_perspective/perspective.py)
- [x] There is a structured decision trace output for explainability and downstream authoring.
  - Evidence: `build_decision_trace()` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## 19) Validation rules

- [x] A validation layer exists for required model fields and semantic consistency.
  - Evidence: [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)
- [x] Missing required values and invalid semantic contracts are rejected.
  - Evidence: [tests/test_schema.py](tests/test_schema.py)

## 20) Agent contract and integration architecture

- [x] The repo's overall design matches the contract's intent: viewpoint -> navigation -> scene reasoning -> authoring.
  - Evidence: [README.md](README.md), [SKILL.md](SKILL.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [x] The project explicitly treats x3d_mcp and x3d_perspective as complementary systems.
  - Evidence: [README.md](README.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [x] The end-to-end integration pipeline is formalized in the schema layer.
  - Evidence: `build_integration_contract()` in [src/x3d_perspective/schema.py](src/x3d_perspective/schema.py)

## Overall assessment

- [x] Strong runtime alignment with the schema's purpose and design
- [x] Strong alignment on viewpoint, navigation, frame, scale, and validation semantics
- [x] Formal schema contract layer implemented and validated
- [x] Contract artifacts exported through the public package API
- [x] The repo now closes the core functional gap in the proposed agentic schema
- [ ] Only the external literal schema artifact layer remains a gap: there is no standalone JSON/YAML/OWL schema file that mirrors the proposal exactly

## Current status summary

The repository now has both a strong runtime perspective engine and an explicit formal schema layer. The implementation is not a literal external ontology file or standalone spec artifact, but it does provide a verified machine-readable contract that matches the project's actual code path and supports downstream authoring, validation, and explainability workflows.

In other words, the remaining gap is not in the perspective engine or contract semantics; it is in delivering a separate, exact external schema artifact that mirrors the proposal word-for-word. The runtime contract and validation layer are already in place and working.
