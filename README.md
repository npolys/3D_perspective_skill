# 3D Spatial Cognition Skill v6

A concept-first, X3D-grounded spatial cognition framework for intelligent agents, digital twins, XR environments, simulation systems, and semantic world modeling.

## Vision

Transform perspective-centric reasoning into a complete model of:
- Perception
- Embodiment
- Navigation
- Visibility
- Collision
- Reachability
- Planning
- X3D interoperability

## Architecture

Concept Layer -> Mapping Contract Layer -> X3D Layer -> Runtime

### Core Concepts
- Perspective
- EmbodiedAgent
- NavigationMode
- ObservationRegion
- OccupancyConstraint
- Plan

### X3D Coverage
- Viewpoint
- NavigationInfo
- VisibilitySensor
- Collision

## Normative vs Derived

### Normative (round-trip preserved)
- NavigationInfo.type
- NavigationInfo.avatarSize
- NavigationInfo.speed
- NavigationInfo.visibilityLimit
- Viewpoint.fieldOfView
- VisibilitySensor.center
- Collision.proxy

### Derived (reasoning outputs)
- PerceptualVolume
- NearPerceptionLimit
- ObservableSet
- ReachableSet
- TraversalCost

## Agent APIs

```python
load_x3d()
export_x3d()
can_see()
is_reachable()
visible_objects()
reachable_spaces()
compute_best_viewpoint()
compute_best_navigation_type()
plan_path()
generate_plan()
```

## Compliance Philosophy

X3D remains the authoritative serialization and runtime representation.
The ontology remains concept-first.
The mapping contract guarantees lossless mapping of supported normative semantics.
