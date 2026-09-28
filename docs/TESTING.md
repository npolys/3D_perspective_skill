# Testing and verification

There are two layers of tests.

- **Offline tests** check the analysis against known values. They need nothing beyond the package.
- **Live tests** check the analysis against real renderers. They open X_ITE and X3DOM in a headless browser.

The live checks are also packaged as `x3d-perspective verify`, so you can run them on your own scenes.

## Running the tests

```
pip install -e .[dev,live]
python -m playwright install chromium
pytest                  # offline: 91 tests, about a second
pytest --live           # also the live tests, about 2 minutes; needs network for the renderers' scripts
```

Live tests carry the `live` marker, and `tests/conftest.py` skips them unless `--live` is given.

| File | What it checks |
|---|---|
| `test_frame.py` | up, gravity, units, Viewpoint scaling of the body and near plane, Z-up detection, the default camera |
| `test_view.py` | projection at 1280×720 against pixels measured in captures; clipping at the frame edge; occlusion; reason codes; WALK settling per renderer; the fall case |
| `test_relations.py` | "right" from each Viewpoint; resolving "that box"; placement, including in a rotated, scaled parent |
| `test_x3d_grounding.py` | every link in `ontology/x3d_grounding.ttl` names a node and field that x3d_mcp's `describe_node` knows, with the same default |
| `test_project_files.py` | the ontology parses; the SKILL.md header is valid; the defaults snapshot matches the spec values the docs quote |
| `test_live.py` (live) | four Viewpoints × X_ITE and X3DOM: live camera, object boxes, and "put that box to the right of the sphere" |
| `test_live_cli.py` (live) | `capture --set` in both renderers; `verify` passing on the room, and failing when the viewer falls |

## What the live checks compare

For each Viewpoint in each renderer, `verify.check_viewpoint` does four things:

1. **Binds the Viewpoint** in the live browser. X_ITE uses `changeViewpoint`; X3DOM uses `set_bind`.
2. **Checks the camera.** The live camera, read through a `ProximitySensor` in X_ITE or `viewMatrix` in X3DOM, must be within **1 cm** of the imagined eye and look the same way. This catches WALK settling differences between renderers.
3. **Captures the view** at 1280×720.
4. **Checks the objects.** It finds every strongly coloured object in the capture and compares it with the imagined view:

| Imagined | In the capture | Result |
|---|---|---|
| visible and unobstructed | found | each edge of the imagined box must lie between the seen `box` and `shadow_box`, within **3 px** |
| visible but partly hidden | found | the seen box must lie inside the imagined outline, within 3 px |
| visible | not found | disagreement: imagined visible, not found |
| not visible | found | disagreement: found, but imagined not visible |
| not visible | not found | agreement |

### Why two boxes

Faces turned away from the lights shade to pure black. An object's own dark rim and a neighbour's shadowed face are then the same `(0, 0, 0)`, so black pixels can't be attributed. `imaging.object_boxes` therefore reports two boxes:

- `box`: the pixels that clearly have the object's hue;
- `shadow_box`: that region extended through touching near-black pixels, up to 8 px.

The object's true outline lies between the two boxes.

## Verifying your own scenes

```
x3d-perspective verify my_scene.x3d --out-dir captures
x3d-perspective verify my_scene.x3d --viewpoint Door --renderer x3dom
```

The exit status is 1 on any disagreement, so `verify` can run in CI. To get useful checks:

- **Give the objects you care about saturated, distinct `Material` colours.** Objects are found by hue. Pale, grey, white and black objects are skipped, and two objects of similar hue are confused.
- **Name objects with `DEF` on their `Transform`.** Objects take the name of their nearest DEF'd ancestor, and `place` moves that Transform.
- **Avoid black materials next to coloured objects.** They look like shaded rims.
- **Stand WALK Viewpoints over support.** Otherwise X_ITE's viewer falls, which `verify` reports as a problem.

## Renderer notes

| | X_ITE 16.4.1 | X3DOM 1.8.3 |
|---|---|---|
| Headless rendering | yes (software GL) | yes, in Chrome's full headless mode (`channel="chromium"`); not in the headless shell |
| WALK eye when a Viewpoint is bound | settled `avatarSize[1]` above support | the authored position, until the user moves |
| Camera readback | `ProximitySensor` `position_changed` and `orientation_changed` | `runtime.viewMatrix().inverse()` |
| Own projection | none | `runtime.calcCanvasPos` (agrees with the skill to within 1 px) |

The versions are pinned in `x3d_perspective.live` (`X_ITE_VERSION`, `X3DOM_VERSION`). When you move to a new version, re-run `pytest --live`. In particular, re-measure `SETTLES_ON_BIND` in `x3d_perspective.perspective`.

## Refreshing the X3D field defaults

`src/x3d_perspective/data/x3d_defaults.json` is a snapshot of x3d_mcp's `describe_node` output. To refresh it from the hosted endpoint:

```
python scripts/snapshot_defaults.py [--url https://x3d-mcp.onrender.com/mcp]
pytest tests/test_project_files.py tests/test_x3d_grounding.py
```

## Continuous integration

`.github/workflows/tests.yml` runs three jobs:

- **offline:** lint plus the offline tests, on Linux and Windows with Python 3.10–3.13;
- **live:** the live tests on Linux;
- **build:** builds the package and checks it with `twine check`.
