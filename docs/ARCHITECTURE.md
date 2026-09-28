# Architecture

## What the skill does, and what it leaves to x3d_mcp

The agent takes the user's perspective on an X3D scene: the 2D view the X3D browser renders from the bound Viewpoint. It can:

- **imagine** that view from the X3D encoding;
- **capture** the rendered view;
- **see** the capture and compare it with what it imagined;
- **act** on the live scene or the document, for example "put that box to the right of the sphere".

[X3D_MAPPINGS.md](X3D_MAPPINGS.md) holds the rules. [REQUIREMENTS.md](REQUIREMENTS.md) lists what was asked for, with its current status.

Claude plans and orchestrates, and calls two tool sources:

- **[x3d_mcp](https://github.com/Web3DConsortium/x3d_mcp)**, the Web3D Consortium MCP server, used as a hosted MCP endpoint at `https://x3d-mcp.onrender.com/mcp`. It owns X3D correctness:
  - schema and DTD validation;
  - semantic checks;
  - node and field definitions;
  - ontology terms;
  - rendering;
  - document edits by DEF name.
- **`x3d_perspective`** (this repo) owns the perspective:
  - world transforms, up and gravity, units and scale;
  - the viewer's body and its coupling with the Viewpoint;
  - the projection to the 2D view: framing, relations and visibility;
  - collision;
  - resolving viewer-relative instructions;
  - driving the live browser view.

Two rules:

- Don't reimplement anything x3d_mcp already provides, including X3D schemas and ontologies.
- Don't ask x3d_mcp for spatial reasoning, because it computes no transforms, bounding boxes or projections.

Claude does the planning, so the old `planning.py`, `goal.schema.json` and `planning.schema.json` are dropped.

| Need | Owner | Tool or module |
|---|---|---|
| Validate a scene (XSD and DTD 4.1, semantic checks) | x3d_mcp | `validate_x3d(content)`, `validate_semantic(content)` |
| Fix containerField errors | x3d_mcp | `modify_x3d_node`; `autofix_x3d` once redeployed |
| Field names, types and per-node defaults | x3d_mcp | `describe_node(node_type)` |
| Capture the rendered view | x3d_perspective, and x3d_mcp | `x3d-perspective capture` (X_ITE or X3DOM, live); x3d_mcp `render_image` (X_ITE) once redeployed |
| Change the document by DEF | x3d_mcp | `modify_x3d_node`, `move_x3d_node`, `remove_x3d_node` |
| Load the scene: world matrices, units, Inline files, triangles | x3d_perspective | `x3d_loader.py`, `geometry.py` |
| Up, gravity, units, meter scale | x3d_perspective | `frames.py` |
| The perspective, including the WALK eye settled on support, per renderer | x3d_perspective | `perspective.py` |
| Imagine the view: pixel boxes, depth, framing, occlusion, reason codes | x3d_perspective | `view.py` |
| Object relations; resolving viewer-relative instructions | x3d_perspective | `relations.py` |
| Drive the live view in X_ITE or X3DOM | x3d_perspective | `live.py` |
| See a capture: where each coloured object landed | x3d_perspective | `imaging.py` |
| Collision paths and passable gaps | x3d_perspective | Phase 4 (support under the eye and under moved objects is already in `perspective.py` and `relations.py`) |

## Capturing and changing the live view

`live.LiveView` opens the scene in X_ITE or X3DOM in headless Chromium through Playwright, at 1280×720 by default. It then binds Viewpoints, sets fields, reads the live camera and captures the canvas.

- The scene's directory is served on a loopback port, so relative URLs work.
- The page itself is served from memory, so nothing is written next to the scene.
- `x3d-perspective capture` wraps it.
- Install with `pip install -e .[live]` and `python -m playwright install chromium`.

Verified in both renderers by `tests/test_live.py`, from the four Viewpoints of `room.x3d`:

| Operation | X_ITE (`x_ite@latest` from jsDelivr) | X3DOM 1.8.3 (x3dom.org) |
|---|---|---|
| Load | `<x3d-canvas src="room.x3d" notifications="false">` | scene children embedded in `<x3d><scene>`, as x3d_mcp's `x3dom_page` does |
| Ready | `canvas.browser.currentScene.rootNodes` is filled | `x3dElement.runtime` is attached (the x3dom-spikes' adapter polls the same) |
| Bind a Viewpoint | `browser.changeViewpoint("Side")` | `[DEF='Side'].setAttribute("set_bind", "true")` |
| Set a field | `currentScene.getNamedNode("Table").translation = new X3D.SFVec3f(…)`, typed from `describe_node` | `[DEF='Table'].setAttribute("translation", "x y z")` |
| Live camera | a world-sized `ProximitySensor`'s `position_changed` and `orientation_changed` (portable X3D) | `runtime.viewMatrix().inverse()` |
| Renderer's own projection | none | `runtime.calcCanvasPos(x, y, z)` |
| Capture | canvas screenshot | canvas screenshot |

**Launch settings.** Chrome's full headless mode (`channel="chromium"`) with SwiftShader software GL, the same flags as x3d_mcp's renderer and the x3dom-spikes. No GPU is needed. X3DOM draws geometry in this mode; it doesn't in the stripped-down headless shell.

The LiveView defaults avoid launching Chromium with `--no-sandbox`. The LiveView API and the CLI expose a `--no-sandbox` / `allow_no_sandbox` option for environments that require it (some CI runners). This option is unsafe on multi-tenant or sensitive hosts — prefer running captures inside a container or VM. Also consider hosting renderer scripts locally instead of pulling from a CDN when capturing untrusted scenes.

**Pitfalls:**
- **A bind takes effect on the next frame.** Wait before reading the camera. `LiveView.bind` waits 2.5 s: the default 1 s transition, then settling.
- **X_ITE overlays the Viewpoint's `description`** after `changeViewpoint`. The page sets `notifications="false"` so it stays out of captures.
- **WALK gravity timing differs by renderer.** X_ITE settles the eye on bind; X3DOM keeps the authored eye ([X3D_MAPPINGS.md §1](X3D_MAPPINGS.md)).
- **Blank frames pass x3d_mcp's render test,** which only checks the PNG is more than 500 bytes. A capture showing only the Background means the viewer fell or the camera faces away. Look at the capture.
- **Black shading is ambiguous.** It can be an object's own rim or a neighbour's shadow. `imaging.object_boxes` therefore reports a box of clearly coloured pixels and one extended through touching black ([X3D_MAPPINGS.md §2](X3D_MAPPINGS.md)).

Once the hosted endpoint has `render_image`, it can take X_ITE still images too. `live.py` stays for what needs a running browser: binding, changing fields, reading the camera, and X3DOM.

## Static X3D reasoning vs runtime perspective

A useful distinction in this project is between what can be understood from the authored X3D file alone and what requires runtime or image-based verification.

From the X3D file and the initial authored Viewpoint and NavigationInfo, the system can determine a great deal about the scene:

- the scene graph structure and parent-child transforms;
- object placement, scale, rotations and local-to-world transforms;
- units, world scale and geometry extents;
- initial Viewpoint pose, fieldOfView, and authored camera intent;
- NavigationInfo defaults such as avatarSize, speed, headlight, and declared navigation type;
- approximate object-level relationships in world space and in the authored camera frame.

This is enough for a strong static world model and for many geometric precomputations: bounding boxes, depth ordering, candidate frustum tests, and likely visibility. A scene loader can therefore reason about object layout and rough perspective before rendering.

However, static authored state is not the same as the actual user perspective. Important facts are not reliably knowable from the file alone:

- the currently bound Viewpoint may differ from the first authored node;
- the currently bound NavigationInfo may switch the active camera policy;
- WALK, FLY, EXAMINE and LOOKAT semantics differ materially in practice;
- the browser may settle the eye on support or preserve the authored pose depending on renderer and runtime state;
- rendering is affected by actual runtime binding, viewport size, occlusion, lighting, transparency, and user navigation;
- the final image may differ from the authored world geometry because of renderer-specific behavior and dynamic scene effects.

That is why the skill treats the perspective as runtime-aware rather than merely authored. The strongest model is: static X3D reasoning + runtime bound state + live verification. This gives a reliable picture of what the user sees, instead of a brittle static approximation.

### How to strengthen static capability

The static case can be made much stronger without relying on preview rendering or image-space analysis:

1. Prefer the currently bound runtime Viewpoint and NavigationInfo whenever available.
2. Model mode-specific camera policies explicitly: WALK, FLY, EXAMINE, LOOKAT, and authored non-grounded poses.
3. Precompute world-space bounding volumes (AABB, OBB, sphere) for each object and use them for frustum and depth prioritization.
4. Add a scene-level BVH for raycasts and occlusion-priority queries.
5. Encode uncertainty: distinguish “definitely visible,” “likely visible,” and “ambiguous without runtime verification.”
6. Pair static reasoning with runtime validation: predict the view, then check against live browser output when available.

This is the core insight behind the project: a correct 3D perspective requires more than the authored geometry. The user’s actual view depends on runtime binding and navigation policy, and the robust AI agent must reason in that frame.

## The hosted endpoint

Checked on 2026-09-28. The hosted build is older than GitHub `main`.

| | Hosted build | GitHub `main` |
|---|---|---|
| Tools | 28 | 34 |
| `render_image`, `render_current_scene` | missing | present (X_ITE through Playwright) |
| `autofix_x3d` | missing | present |
| `query_ontology`, `node_parents`, `describe_ontology_term` | missing | present, but with the 4.0 ontology |
| Node definitions (X3DUOM) | 4.1: 265 nodes, including the 4.1-only `InlineGeometry` | 4.1 |
| `x3dom_page` default size | 800×600 px | 800×600 px; 1280×720 with the patch in [`upstream/x3d_mcp/`](../upstream/x3d_mcp/) |

Because it runs over HTTP, x3d_mcp disables `path` input in every tool. So:

- **Documents go inline as `content`.** The analyzer runs locally, since it needs the files anyway.
- **Inline files don't resolve on the server.** `emit --flatten` expands each Inline in place, inside a `Transform` whose scale reconciles that file's `unit` statement with the parent's.

## Configuring the endpoint in Claude Code

[`.mcp.json`](../.mcp.json) at the repo root:

```json
{
  "mcpServers": {
    "x3d": { "type": "http", "url": "https://x3d-mcp.onrender.com/mcp" }
  }
}
```

The tools then appear to Claude as `mcp__x3d__<tool>`, for example `mcp__x3d__validate_x3d`.

## Validate before analyzing

A wrong containerField passes XSD validation, but the browser silently drops the node. If the skill imagined that node, its prediction would disagree with the screenshot. So every workflow starts with `validate_semantic`, and containerField errors are fixed before analysis.

## Example workflow: "Put that box to the right of the sphere"

1. **Validate.** Call `validate_x3d(content=…)` and `validate_semantic(content=…)`.
2. **Frame.** Run `x3d-perspective frame scene.x3d`. It returns up, gravity, units and scale.
3. **Take the perspective.** Use the bound Viewpoint, or the live camera if the user has navigated, and the renderer the user is viewing in (`--viewpoint`, `--renderer`). Under WALK, the eye settles on support as that renderer does it.
4. **Imagine.** Run `x3d-perspective see` to get the objects in view, with their pixel boxes, depths and reason codes.
5. **Resolve.** `x3d-perspective resolve SCENE "that box"` finds a free-standing box in view. Then `x3d-perspective place SCENE Table "right of" Lamp` gives the new `translation` in the box's parent frame, and the imagined view after the move.
6. **Apply.** Change the live scene through the X_ITE or X3DOM API (`capture --set`), or change the document with `modify_x3d_node`.
7. **Capture and see.** `x3d-perspective capture` confirms the box appears right of the sphere. Look at the PNG too. Re-validate any document change.

## View size

- **The default is HD 720p: 1280×720 (16:9)**, for both X_ITE and X3DOM.
- The skill passes the size explicitly, because the deployed x3d_mcp still defaults to 720×540 (`render_image`) and 800×600 px (`x3dom_page`). The patch in [`upstream/x3d_mcp/`](../upstream/x3d_mcp/) changes those defaults.
- `fieldOfView` spans the height at 16:9. The focal length is 869.1 px, and the horizontal field of view is 72.7° at the default 0.7854 rad.
- The size used to imagine the view must equal the size it is captured at.

## Input scope

- **XML (`.x3d`) only.** `convert_x3d` accepts only XML as its source, and the scene-editing tools accept only XML.
- **lxml parser**, the same one x3d_mcp's scene-editing tools use.
- **Emitted documents** use X3D 4.1 with the 4.1 DOCTYPE and schema location, as in `examples/room_inspection/room.x3d`.

## Field defaults

`describe_node` serves per-node definitions from X3DUOM 4.1.

- [`scripts/snapshot_defaults.py`](../scripts/snapshot_defaults.py) keeps a local snapshot, shipped as package data in [`src/x3d_perspective/data/x3d_defaults.json`](../src/x3d_perspective/data/x3d_defaults.json): 43 nodes and 781 fields from the hosted endpoint, taken on 2026-09-28.
- `tests/test_x3d_grounding.py` checks every grounded node, field and default in `ontology/x3d_grounding.ttl` against it.

## Ontology version

The grounding uses the X3D Ontology **4.1** namespace, `https://www.web3d.org/specifications/X3dOntology4.1#`.

Checking that `x3d:` terms exist is x3d_mcp's job, through `describe_ontology_term` and `query_ontology`. Its `main` branch bundles the 4.0 ontology, so it needs the 4.1 file (proposed change 3) before those checks can run.

## Packaging

## BVH hot-path integration and tuning

The geometry module implements an optional Bounding Volume Hierarchy (BVH) builder and BVH-aware raycast to accelerate occlusion and ray queries on large scenes. The repository ships conservative defaults tuned from the benchmark harness in examples/benchmarks.

Defaults and environment overrides

- Default method: median-split. (geometry.BVH_DEFAULT_METHOD)
- Default leaf size: 24 triangles. (geometry.BVH_DEFAULT_LEAF)
- Hot-path threshold: view uses a BVH when occluder triangle count >= 2000.

These values are conservative: median-split with a modest leaf size gives reliable amortized speedups for clustered geometry and directional/coherent ray workloads while avoiding excessive build costs for uniform terrain scenes. If tuning is required for a deployment, the following environment variables may be used to change builder defaults before running:

- X3D_PERSPECTIVE_BVH_METHOD = "median" | "sah"
- X3D_PERSPECTIVE_BVH_LEAF = integer leaf size (e.g., 24, 48)

The Scene.bvh accessor reads these environment variables when building the cached BVH tree. The hot-path threshold is a conservative default to avoid build-amortization in small scenes; change it in code if a different policy is preferred.

The BVH is used transparently for visibility queries when available. If the BVH is absent or explicitly unsuitable, the raycast falls back to the brute-force triangle test. Future releases may expose a CLI flag or environment variable to change the threshold and enable async/lazy BVH construction to avoid first-frame stalls.


## Packaging

```
src/x3d_perspective/   Python library, no MCP dependency (numpy, lxml; Playwright and Pillow for [live])
  x3d_loader.py          .x3d to world-space records: Viewpoints, NavigationInfo, shapes as triangles, units
  geometry.py            triangles for X3D geometry nodes; ray casting
  mathx.py               SFRotation, Transform matrices
  frames.py              up, gravity, units, extent, objects: `frame`
  perspective.py         bound Viewpoint + NavigationInfo -> eye, axes, body, near and far planes, WALK settling
  view.py                the imagined view: pixel boxes, depth, framing, occlusion, reason codes: `see`
  relations.py           viewer-relative directions, `resolve`, `relate`, `place`
  live.py                drives X_ITE or X3DOM in a browser: bind, set fields, read the camera, capture
  imaging.py             sees a capture: where each coloured object landed
  cli.py                 `x3d-perspective` command line: what SKILL.md tells Claude to run
  mcp_tools.py           Phase 5: register(mcp) in x3d_mcp's style
SKILL.md                 the workflow across both tool sources
```

## Proposed x3d_mcp changes

0. **Redeploy the hosted endpoint from `main`, with the patch in [`upstream/x3d_mcp/`](../upstream/x3d_mcp/).**
   - The patch sets the HD 1280×720 default size and pins `mcp<2`.
   - Without the pin, a fresh build fails at import.
   - x3d_mcp's tests pass with the patch: 283 passed, 2 skipped.
   - `render_image` on the hosted server also needs the Dockerfile to install the `[render]` extra and Chromium.
1. **`render_image` options:**
   - `viewpoint_def=…` to render from a named Viewpoint;
   - `renderer="x_ite"|"x3dom"`;
   - a non-blank check, since today a Background-only frame passes the render test.
2. **Perspective checks in `validate_semantic`.** Its only viewpoint check today is "no Viewpoint". Candidates:
   - WALK with no support under the initial Viewpoint, so the viewer falls and the view is blank;
   - a Viewpoint whose authored height differs from `avatarSize[1]` above its support;
   - a Viewpoint under a non-uniform scale;
   - `nearDistance` greater than or equal to `farDistance`;
   - `RigidBodyCollection.gravity` not parallel to −up;
   - a `unit` length statement with `avatarSize` omitted.
3. **Bundle `X3dOntology4.1.ttl`** to match X3DUOM 4.1. Also report the `x3d:navigationInfo` property-type defect upstream.
4. **Accept ClassicVRML and JSON** as `convert_x3d` sources.

## Phases

| Phase | Deliverables | Done when |
|---|---|---|
| 0. Setup (done) | pyproject, SKILL.md header, parseable ontology, `.mcp.json`, defaults snapshot | `pip install -e .` works; tests pass |
| 1. Frame (done) | lxml loader, Inline resolution, world matrices, up and gravity, units, meter scale; `frame` command | Met (`tests/test_frame.py`): Z-up content is detected; a centimeter `unit` statement gives meters; a Viewpoint under a 0.1 scale gives `r` = 0.025 m, `h` = 0.16 m, near plane = 0.0125 m |
| 2. Imagine, capture, see (done) | perspective with the WALK eye settled per renderer; `see`; `live.py`; `imaging.py`; `capture` | Met (`tests/test_view.py`, `tests/test_live.py`): imagined boxes within 3 px of X_ITE and X3DOM captures from four Viewpoints; the live camera within 1 cm of the imagined eye; the fall case predicted |
| 3. Relations and instructions (done) | viewer-relative directions; `resolve`, `relate`, `place`; apply live | Met (`tests/test_relations.py`, `tests/test_live.py`): "right of the sphere" from all four Viewpoints in both renderers, confirmed by capture |
| 4. Collision | collidable set, steps, passable gaps, paths. Occlusion and reason codes are already in `view.py` | Glass blocks movement but not sight; a 0.45 m doorway blocks the default body |
| 5. MCP | `mcp_tools.py`; upstream pull requests | The same tools work as a sidecar endpoint |
| 6. Ontology | SHACL shapes; RDF export | SHACL validates exported perspective records |
