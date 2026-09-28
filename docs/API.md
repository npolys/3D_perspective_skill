# Python API

```python
import x3d_perspective as xp
```

The top-level package covers the analysis and needs only NumPy and lxml. Live capture (`x3d_perspective.live`) and verification (`x3d_perspective.verify`) need the `live` extra: Playwright and Pillow.

## Load a scene

```python
scene = xp.load("room.x3d")        # -> xp.Scene
```

`load` parses X3D XML safely: no DTD loading, no entity expansion, no network. It converts everything to world space in meters:

- `Transform` chains, including `center`, `scaleOrientation` and the same fields on HAnim and CAD nodes;
- the length `unit` statement, per file, including Inline files;
- `Switch`, `visible='false'`, `Collision` and its `proxy`, and `LOD` (its first level);
- geometry as triangles: Box, Sphere, Cylinder, Cone, IndexedFaceSet, IndexedTriangleSet, TriangleSet, IndexedQuadSet, QuadSet, ElevationGrid.

`Scene` fields:

| Field | Meaning |
|---|---|
| `unit`, `unit_source` | meters per scene unit, and where that came from |
| `viewpoints` | `Viewpoint` records in file order; the first is bound at load |
| `navigation_infos` | `NavigationInfo` records; the first is bound at load |
| `shapes` | `ShapeRecord` per Shape: `object`, `geometry`, `triangles` (world, meters), `diffuse_color`, `transparency`, `solid`, `rendered`, `collidable`, `mover` (the DEF'd Transform to move it) |
| `background_sky`, `fog_range`, `notes` | the Background sky color, the Fog range, and anything left out |

Useful methods: `scene.viewpoint(name)`, `scene.objects()` (object name → its shapes), `scene.triangles(rendered=…, collidable=…, exclude=…)`.

Field defaults come from `x3d_perspective.x3d_loader.default(node_type, field)`: x3d_mcp's `describe_node` output, shipped as package data.

## Take a perspective

```python
p = xp.from_viewpoint(scene, "Overlook", renderer="x_ite")      # -> xp.Perspective
p.eye, p.forward, p.up, p.directions()["right of"]
p.summary()                                                      # JSON-ready
```

`renderer` is `"spec"`, `"x_ite"` or `"x3dom"`. Under WALK, `spec` and `x_ite` settle the eye `avatarSize[1]` above the support below it when a Viewpoint is bound; `x3dom` keeps the authored eye. With no support, `p.falls` is true and `p.eye` is `None`.

With no name, the initially bound Viewpoint is used, or the X3D default camera (`0 0 10`, looking along −Z) if the scene has none.

`Perspective` fields:

| Field | Meaning |
|---|---|
| `eye`, `authored_eye` | the effective and the authored eye position |
| `right`, `camera_up`, `forward` | the camera axes |
| `up` | +Y of the Viewpoint's parent frame (gravity is `-up`) |
| `field_of_view`, `near`, `far` | the view volume; `near` is `avatarSize[0] / 2` unless `nearDistance` is set |
| `collision_radius`, `eye_height`, `step_height`, `speed` | the body, scaled by the Viewpoint's parent transforms and the unit statement |
| `walk`, `falls`, `support`, `notes` | WALK gravity applied, the viewer fell, what it stands on, and remarks |

`p.directions()` gives the viewer-relative directions `right of`, `left of`, `in front of`, `behind`, `above` and `below` as world vectors.

## Imagine the view

```python
view = xp.see(scene, p, size=(1280, 720))
{o["name"]: (o["status"], o.get("pixel_box")) for o in view["objects"]}
```

The fields are listed in [CLI.md](CLI.md#see-the-imagined-view). Lower-level helpers are in `x3d_perspective.view`:

- `project(p, points, width, height)` returns pixels and depths;
- `focal_px(p, width, height)` returns the focal length in pixels.

## Frame, relations and placement

```python
xp.frame(scene)                                        # up, gravity, units, extent, objects
xp.resolve(scene, p, "that box")                       # {"match": "Table", ...}
xp.relations_between(scene, p, "Table", "Lamp")        # {"relations": ["right of", "in front of", "below"], ...}
plan = xp.place(scene, p, "Table", "right of", "Lamp", gap=0.1)
plan["set_field"]                                      # {"def": "Table", "field": "translation", "value": "-0.55 0.375 -1"}
```

`x3d_perspective.relations` also provides:

- `with_translation(scene, def_name, value)` returns a copy of the scene with a Transform's translation set;
- `moved_scene(scene, name, delta)` returns a copy with one object moved.

Use them to imagine a change before making it.

## Schema-shaped perspective outputs

The package also exports a schema layer for downstream consumers that do not want to reason directly from runtime objects.

```python
import x3d_perspective as xp

scene = xp.load("room.x3d")
model = xp.build_perspective_model(scene, viewpoint="Entry", renderer="spec")
errors = xp.validate_perspective_model(model)

if errors:
    raise ValueError(errors)

skill = xp.build_skill_contract()
taxonomy = xp.build_taxonomy_contract()
trace = xp.build_decision_trace(
    model_type=model.perspective_type,
    navigation_mode=model.navigation_mode,
    scene_context="museum",
)
integ = xp.build_integration_contract()
```

The schema API is intentionally small and explicit:

- `build_perspective_model(...)` returns a `PerspectiveModel` with the perspective type, coordinate frame, scale class, navigation mode, camera profile, semantic inputs, viewpoints, affordances, and accessibility features.
- `validate_perspective_model(model)` checks the required contract fields and taxonomy consistency rules.
- `build_skill_contract()` returns the machine-readable `SkillContract` object.
- `build_taxonomy_contract()` exposes the perspective taxonomy, viewpoint taxonomy, and observer profile.
- `build_environment_rule_table()` maps scene context to navigation and camera choices.
- `build_decision_trace(...)` produces an explainability trace for downstream rendering or authoring.
- `build_integration_contract()` describes the pipeline from ontology/context inference to downstream authoring.

These functions are exported at the package top level via `x3d_perspective` and are covered by `tests/test_schema.py`.

## Drive the live view

```python
from x3d_perspective.live import LiveView

with LiveView("room.x3d", renderer="x3dom", size=(1280, 720)) as live:
    live.bind("Side")                                   # set_bind / changeViewpoint
    live.set_field("Table", "translation", "-1.5 0.375 -1.75")
    live.camera()                                       # {"position", "right", "up", "forward"}
    live.project([[-1.5, 1.2, -1.0]])                   # X3DOM's own calcCanvasPos; None for X_ITE
    png = live.capture("side.png")
    live.errors                                         # JavaScript errors from the page
```

`LiveView` runs headless Chromium with software GL through Playwright, and serves the scene's directory on a loopback port. The renderer versions are pinned: X_ITE 16.4.1 and X3DOM 1.8.3. Override them with `x_ite_version=` and `x3dom_version=`.

LiveView constructor notes

- `LiveView(scene_path, renderer='x_ite'|'x3dom', size=(1280,720), allow_no_sandbox=False, launch_args=None)`
  - `allow_no_sandbox`: when True, appends `--no-sandbox` to Chromium's launch args. Defaults to False to avoid running Chromium without its sandbox. Set True only in trusted or isolated CI environments that require it.
  - `launch_args`: optional list that overrides the default Chromium launch arguments entirely (useful to pin flags or run with a custom configuration).

When capturing untrusted scenes, run captures in an isolated environment (container, VM or dedicated job runner), and prefer local renderer scripts rather than fetching from CDNs.

## See a capture, and verify

```python
from x3d_perspective import imaging, verify

seen = imaging.object_boxes(png, verify.object_colors(scene))   # name -> {"box", "shadow_box"} or None
verify.compare(view, seen)                                      # per-object agreement
report = verify.verify("room.x3d", out_dir="captures")          # every Viewpoint, both renderers
report["ok"]
```

[TESTING.md](TESTING.md) explains the checks. `verify.check_viewpoint(session, scene, viewpoint)` checks one Viewpoint in an open `LiveView`.

## Command line

`x3d_perspective.cli.main(argv)` runs the `x3d-perspective` command; see [CLI.md](CLI.md).
