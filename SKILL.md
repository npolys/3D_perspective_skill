---
name: x3d-perspective
description: Take the user's perspective on an X3D scene. Imagine, capture and see the 2D view that X_ITE or X3DOM renders from the bound Viewpoint; understand world, body and image scale, framing and object relations from that view; and turn viewer-relative instructions such as "put that box to the right of the sphere" into X3D field changes, live or in the document. Grounded in Viewpoint, NavigationInfo (WALK gravity, collision, avatarSize), Transform and unit. Uses the x3d MCP server for validation, node definitions and rendering.
---

# X3D perspective

The perspective is the 2D view the X3D browser renders from the bound Viewpoint. Every rule here is grounded in `docs/X3D_MAPPINGS.md`, with X3D spec clauses cited there.

The project also exposes a schema layer for downstream integration. The runtime engine produces a perspective; `x3d_perspective.schema` normalizes that into `PerspectiveModel`, validates it with `validate_perspective_model`, and exposes `SkillContract`, taxonomy, environment rules, decision traces, and an integration contract for authoring workflows.

## Commands

Install once with `pip install -e .[live]` in this folder, then `python -m playwright install chromium`. Each command prints JSON, and each takes `--viewpoint DEF` and `--renderer x_ite|x3dom`. Pass the renderer the user is viewing in, because the two differ under WALK (below). `docs/CLI.md` documents every field.

| Command | What it gives |
|---|---|
| `x3d-perspective frame SCENE` | up, gravity, units, extent in meters, the body, each Viewpoint's authored and effective eye, the objects |
| `x3d-perspective see SCENE` | the imagined 1280×720 view: per object, its pixel box, depth, cut-off edges, third of the frame, visible fraction and reason code |
| `x3d-perspective resolve SCENE "that box"` | which object a phrase means from this view, or the candidates to ask about |
| `x3d-perspective relate SCENE FIGURE GROUND` | which relations hold from this view: right of, in front of, above, and their opposites |
| `x3d-perspective place SCENE FIGURE "right of" GROUND` | the field change that makes it true (`set_field`), and the imagined view after the change |
| `x3d-perspective capture SCENE --renderer … --out view.png [--set DEF.field=VALUE]` | a capture from the live renderer, the live camera, and seen versus imagined boxes. Look at the PNG as well |
| `x3d-perspective verify SCENE [--out-dir DIR]` | every Viewpoint in both renderers, compared with the imagined view; exit status 1 on any disagreement |

## Rules that set the view

- **Up** is +Y of the bound Viewpoint's parent coordinate system. The Viewpoint's own `orientation` does not change it.
- **WALK has gravity and collision detection**, and `avatarSize` sets both:
  - `avatarSize[0]` is the collision distance, and the near clipping plane is `avatarSize[0] / 2`;
  - `avatarSize[1]` is the eye height held above the terrain;
  - `avatarSize[2]` is the tallest step.
- **Under WALK the authored eye height is only a start.** Gravity pulls the eye along −up onto support, and it then rides at `avatarSize[1]` above it. With no support the viewer falls, and the view shows only the Background.
- **When that happens depends on the renderer.** X_ITE settles the eye as soon as a Viewpoint is bound. X3DOM 1.8.3 keeps the authored eye until the user moves. `--renderer` accounts for this.
- **Spec defaults:**
  - `Viewpoint`: position `0 0 10`, orientation `0 0 1 0`, fieldOfView `0.7854` (spanning the smaller side of the view);
  - `NavigationInfo`: avatarSize `0.25 1.6 0.75`, type `"EXAMINE" "ANY"`.

  Together they make an object viewer with no gravity.
- **Scaling.** `avatarSize`, `speed` and `visibilityLimit` scale with the Viewpoint's parent transforms. The `unit` statement converts lengths to meters.

## Imagine, capture, see

1. **Imagine** the screenshot. At the default 1280×720, the focal length is `f_px = (min(W,H)/2) / tan(fov/2)` = 869.1 px. Project each object with `u = W/2 + f_px·x/z` and `v = H/2 − f_px·y/z`, in camera coordinates. For each object, report:
   - its pixel box, and any frame edges that cut it off;
   - its depth;
   - its share of the frame;
   - its reason code if it isn't visible.
2. **Capture** the real view at the same size with `x3d-perspective capture`, in X_ITE or X3DOM. `render_image` on the x3d MCP server also works where it's deployed, but X_ITE only.
3. **See**: look at the screenshot and compare it with what you imagined. `capture` also compares them for strongly coloured objects. It finds each object by colour, and reports two boxes, because shading at object edges goes black, and black pixels could belong to either the object or its neighbour.

   A frame showing only the Background means one of three things:
   - the viewer fell;
   - the camera is facing away from the content;
   - the content is clipped by the near or far plane.

   An object that's missing was dropped, is hidden, or is unlit.

## Scale, framing and relations

- **Name the scale you're using:**
  - world: meters;
  - body: body widths `2·avatarSize[0]`, eye heights, steps;
  - image: pixels, or a fraction of the frame.
- **Framing:**
  - in frame, cut off at an edge, or behind the viewer;
  - in the left, centre or right third of the frame;
  - apparent size in pixels.

  To make an object appear `p` px tall, stand `f_px · size / p` away.
- **Relations** use the viewer's frame by default:
  - `right = level(view direction) × up`, and left is its opposite;
  - "in front of X" means toward the viewer; "behind X" means farther away;
  - above and below follow up.

  If the reference object has its own front (a humanoid, a chair, a car), say which frame you're using or ask.

## Instructions like "put that box to the right of the sphere"

1. **Resolve "that box"** with `resolve` to a free-standing object in view, not the floor or a wall. If more than one fits, ask.
2. **Take the viewer's current perspective.** Use the live camera if the user has navigated; otherwise use the bound Viewpoint, and the renderer the user is viewing in.
3. **Place the object** with `place`: new centre = sphere centre + `right · (sphere radius + the box's half-width along right + a small gap)`. The box is kept resting on its support, and the new `translation` is expressed in the box's parent frame.
4. **Apply the move** in the box's parent coordinates:
   - live in X_ITE: `browser.currentScene.getNamedNode("DEF").translation = new X3D.SFVec3f(x, y, z)`;
   - live in X3DOM: `element.setAttribute("translation", "x y z")`;
   - in the document: `modify_x3d_node`.
5. **Check the result:** `capture --set Table.translation="…"` captures the new view, and the box should be right of the sphere in the image. Re-validate any document change with `validate_x3d`.

## Reporting

- Give each distance in meters and in body units.
- Give positions in the image as pixels or thirds of the frame.
- Name the frame: the world, "from your view", or the object's own.
- Cite the X3D node and field behind each number.
- Say when units were inferred rather than declared.

## Relationship with x3d_mcp

The skill is intentionally paired with the Web3D Consortium's [x3d_mcp](https://github.com/Web3DConsortium/x3d_mcp) server, and the boundary is explicit:

- **x3d_mcp owns standards, validation and document correctness.**
  - `validate_x3d`, `validate_semantic`
  - `describe_node` and default fields
  - ontology and grounding terms
  - document edits such as `modify_x3d_node`, `move_x3d_node`
  - rendering when the hosted endpoint can provide it
- **x3d_perspective owns runtime perspective and spatial reasoning.**
  - the effective camera from the bound Viewpoint and NavigationInfo
  - WALK/FLY/EXAMINE mode policy
  - world units, up, gravity, support, collision and body scale
  - projection, visibility, object framing and occlusion
  - viewer-relative relations and translate-to-scene-edit actions

This split matters in practice. x3d_mcp answers “what is the X3D object model and is the document valid?”; x3d_perspective answers “what does the user actually see and what should be changed from that view?” In other words, x3d_mcp provides the authoritative X3D document-level facts, while this skill performs viewpoint-aware spatial reasoning in the camera frame.

The hosted server accepts documents only as `content` and has no `render_image` yet. `src/x3d_perspective/data/x3d_defaults.json` is a snapshot of its `describe_node` output.
