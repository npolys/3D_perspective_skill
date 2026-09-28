# X3D grounding for perspective-taking

The agent takes the user's perspective on an X3D scene: the 2D view the X3D browser renders from the bound Viewpoint. This document ties everything the agent reasons with to X3D 4.1 nodes, fields and default values:

- up and gravity;
- the viewer's body and its scale;
- what appears where in the view;
- how objects relate to each other from that view.

Normative quotes are from ISO/IEC 19775-1, Navigation component (clause 23). They were checked in both V4.0 and the V4.1 draft, and the wording is the same. Ontology terms use the Web3D X3D Ontology 4.1:

```turtle
@prefix x3d: <https://www.web3d.org/specifications/X3dOntology4.1#> .
```

## 1. A perspective is the bound Viewpoint plus the bound NavigationInfo

An agent's perspective is fully determined by four things:

1. The currently bound `X3DViewpointNode` (`Viewpoint`, `OrthoViewpoint` or `GeoViewpoint`).
2. The currently bound `NavigationInfo`, or the one referenced by the Viewpoint's `navigationInfo` field (new in X3D 4).
3. The **Viewpoint frame** `V`: the accumulated transform of the Viewpoint's ancestors. `V` excludes the Viewpoint's own `position` and `orientation`.
4. The scene's `unit` statements.

Notation: `s` is the uniform scale of `V`. `u` is the length `conversionFactor` (meters per scene unit; 1.0 when there is no `unit` statement). `R` is the rotation given by `Viewpoint.orientation`.

| Quantity | Source field | Formula | Value with X3D defaults |
|---|---|---|---|
| Up | Viewpoint frame `V` | `normalize(V_rot · +Y)` | `(0, 1, 0)` |
| Gravity direction | Up | `−up` | `(0, −1, 0)` |
| Eye position | `Viewpoint.position` | `V · position`, times `u`; under WALK, settled onto support (below) | `(0, 0, 10)` m |
| View direction | `Viewpoint.orientation` | `V_rot · R · (0, 0, −1)` | `(0, 0, −1)` |
| Camera up | `Viewpoint.orientation` | `V_rot · R · (0, 1, 0)` | `(0, 1, 0)`, but can differ from Up |
| Collision radius `r` | `NavigationInfo.avatarSize[0]` | `avatarSize[0] · s · u` | 0.25 m |
| Eye height `h` | `NavigationInfo.avatarSize[1]` | `avatarSize[1] · s · u` | 1.6 m |
| Step height `k` | `NavigationInfo.avatarSize[2]` | `avatarSize[2] · s · u` | 0.75 m |
| Near plane | `nearDistance`, else `avatarSize[0]` | `nearDistance · s · u` if not −1, else `r / 2` | 0.125 m |
| Far plane | `farDistance`, else `visibilityLimit` | `farDistance · s · u` if not −1, else `visibilityLimit · s · u` if > 0, else ∞ | ∞ |
| Speed | `NavigationInfo.speed` | `speed · s · u` | 1.0 m/s |
| Field of view | `Viewpoint.fieldOfView` | angle across the smaller display dimension | 0.7854 rad (45°) |

Scaling rule (23.4.4): *"The speed, avatarSize and visibilityLimit values are all scaled by the transformation being applied to the currently bound X3DViewpointNode node."*

- A Viewpoint inside `<Transform scale='0.1 0.1 0.1'>` is a miniature observer, with a 0.16 m eye height and a 0.0125 m near plane.
- The near plane follows `avatarSize[0]`, so it shrinks and grows with the body.
- If `s` is non-uniform, the body is ill-defined. The skill reports this rather than picking an axis.

### The spec defaults frame an object, not a walk

These are the defaults from the X3D spec, confirmed by x3d_mcp's `describe_node`:

| Field | Default | What it does to the view |
|---|---|---|
| `Viewpoint.position` | `0 0 10` | 10 m back from the origin, with the eye at y = 0 |
| `Viewpoint.orientation` | `0 0 1 0` | looking along −Z, toward the origin |
| `Viewpoint.fieldOfView` | `0.7854` | 8.28 m of height is visible at 10 m (14.7 m of width at 16:9) |
| `Viewpoint.nearDistance`, `farDistance` | `−1`, `−1` | near plane `r / 2` = 0.125 m; far plane ∞ |
| `NavigationInfo.avatarSize` | `0.25 1.6 0.75` | collision radius, eye height, step height |
| `NavigationInfo.type` | `"EXAMINE" "ANY"` | no gravity or terrain following |

X3D is right-handed with +Y up. The default camera sits at (0, 0, 10) and looks along −Z toward the origin, with +X to the right.

Together these defaults set up an object viewer: a model at the origin, seen from 10 m. A default 2 m `Box` is 193 px tall in a 1280×720 frame, 27% of its height.

This was verified in X_ITE at 1280×720, with a scene containing no Viewpoint or NavigationInfo, so the spec defaults applied:

| Object | Predicted | Rendered |
|---|---|---|
| Default 2 m `Box` at the origin (front face) | u 543–737, v 263–457 | the same pixels |
| Marker at +X | (901, 360) | right of centre |
| Marker at +Y | (640, 99) | above centre |
| Marker at +Z | covers the box, radius 37 px | covers the box, radius 37 px |

The background rendered black (the default `Background.skyColor` `0 0 0`), and the box was lit by the default headlight.

The default eye at y = 0 does not match the 1.6 m eye height. That is harmless in EXAMINE, but it matters as soon as the navigation type is WALK.

### Under WALK, `avatarSize` overrides the authored eye height

Under WALK, the authored `Viewpoint.position` is only a starting point:

1. Gravity drops the eye along −up until it finds support.
2. Terrain following then holds the eye `h` (`avatarSize[1]`) above that support.
3. If nothing is below, the viewer keeps falling, and the view shows only the Background.

So the effective eye is:

- **WALK:** `support point + h · up`;
- **EXAMINE, ANY, LOOKAT, EXPLORE, NONE, and FLY when gravity is off:** the authored position.

The spec does not say *when* WALK gravity starts, and the renderers differ. Measured with the live camera at the `Overlook` Viewpoint of `room.x3d`, authored at 2.8 m under WALK:

| Renderer | On binding a WALK Viewpoint | Live eye at `Overlook` |
|---|---|---|
| X_ITE | settles the eye onto support at once | 1.6 m |
| X3DOM 1.8.3 | keeps the authored eye until the user moves | 2.8 m |

So the imagined view needs to know which renderer the user is looking through (`--renderer`).

Verified in X_ITE with `examples/room_inspection/room.x3d` at 1280×720:

- **Same image from a different authored height.** A WALK Viewpoint authored at y = 3 rendered a pixel-identical image (same SHA-256) to one at y = 1.6 over the same floor.
- **EXAMINE keeps the authored height.** Authored at y = 3, EXAMINE rendered a different view.
- **No support means a fall.** A WALK Viewpoint just past the floor's edge rendered only the Background colour.

## 2. The 2D view: imagining the screenshot

The agent works with the rendered view in three ways:

- **Imagine** it: predict the screenshot from the X3D encoding, using the rules below.
- **Capture** it: take the real screenshot from X_ITE or X3DOM at the same size (see [ARCHITECTURE.md](ARCHITECTURE.md#capturing-and-changing-the-live-view)).
- **See** it: look at the captured image and compare it with the prediction.

When the prediction and the screenshot disagree, something in the scene's encoding is wrong. Typical causes are a dropped node, missing light, an eye that fell or the wrong units.

### Projection

For a world point `P`, with the effective eye `E` and camera axes right `r`, camera up `c` and forward `f` from §1:

```
d   = P − E
x_c = r·d      y_c = c·d      z_c = f·d          (z_c is depth, positive in front)

f_px = (min(W, H) / 2) / tan(fieldOfView / 2)     focal length in pixels
u    = W/2 + f_px · x_c / z_c                     pixels from the left
v    = H/2 − f_px · y_c / z_c                     pixels from the top
```

- **At the default HD size of 1280×720,** `f_px` = 869.1 px at the default 0.7854 rad. The horizontal field of view is 72.7°.
- **In frame:** `near ≤ z_c ≤ far` and `0 ≤ u < W`, `0 ≤ v < H`. If an object's projected box crosses an edge, report which edges cut it off.
- **Apparent size:** `f_px · size / z_c` pixels. A 1.7 m person 10 m away is 148 px tall in a 720 px frame.
- **Depth order:** where projected boxes overlap, the object with the smaller `z_c` is drawn in front, if it is opaque (§7).

These rules were checked against captures:

- **x3d_mcp's smoke test.** The prediction for its 2 m box seen from 6 m was u 466–814, v 186–534, and X_ITE drew it at exactly those pixels.
- **room.x3d, automatically, in both renderers.** `tests/test_live.py` binds each of the four Viewpoints (Entry, Side, Corner, Overlook) in both X_ITE and X3DOM. For each one it checks three things:
  - the live camera is where the imagined eye is, to within 1 cm;
  - each coloured object's box in the capture matches the imagined box, to within 3 px;
  - X3DOM's own `calcCanvasPos` agrees with the projection to within 1 px.
- **Clip the outline, not the box.** Where an object crosses the frame edge, each projected triangle is clipped to the frame. Clipping only the object's box would claim pixels outside the object.
- **Black shading is ambiguous.** Faces turned from the lights render as pure black, both on an object's own rim and on a neighbour's shadowed face. So a seen box is bounded by the clearly coloured pixels on one side and the touching black pixels on the other.

### What else shapes the pixels

These node definitions and defaults come from x3d_mcp's `describe_node`:

| Node.field | Default | Effect on the screenshot |
|---|---|---|
| `Background.skyColor` | `0 0 0` | fills every pixel not covered by geometry: black by default |
| `NavigationInfo.headlight` | `true` | a light at the eye; without it and without other lights, geometry renders dark |
| `DirectionalLight.direction`, `intensity`, `global` | `0 0 −1`, `1`, `false` | parallel light. With `global` false it lights only its own group. Lights never illuminate lines or points |
| `Material.diffuseColor`, `transparency` | — , `0` | object colour; transparent objects show what is behind them |
| `Fog.visibilityRange` | `0` | 0 disables fog; otherwise distant geometry fades to the fog colour |
| `Viewport.clipBoundary` | `0 1 0 1` | the fraction of the window a layer draws into (left, right, bottom, top) |
| `LayerSet.order` | `0` | layers are drawn in this order, each with its own bound Viewpoint |
| `ScreenGroup` | — | *"one unit is equal to one pixel"*: HUD content stays the same pixel size at any distance |
| `Billboard.axisOfRotation` | `0 1 0` | turns its local +Z toward the viewer, so its projected shape depends on the perspective |

Renderer notes:

- **X_ITE** draws HAnim humanoids and PhysicalMaterial, and draws geometry under headless software GL. After `changeViewpoint` it overlays the Viewpoint's `description` on the view, and the overlay appears in captures.
- **X3DOM 1.8.3** does not draw HAnim humanoids or PhysicalMaterial.
  - In Chrome's stripped-down headless shell it clears only the background.
  - In Chrome's full headless mode with SwiftShader (Playwright channel `chromium`, as the x3dom-spikes use) it renders fully, with no GPU.
  - Its WALK timing differs from X_ITE's (§1).

A capture that shows only the Background colour means no geometry reached the frame. Check, in this order:

1. the viewer fell (WALK with no support);
2. the camera points away from the content;
3. the content is beyond the far plane or closer than the near plane;
4. the browser dropped the node because of a wrong containerField.

## 3. Scale, framing and object relations

### Scale

The agent keeps three scales apart and says which one it is using:

- **World scale:** meters, from `unit` statements and `Transform` scale (§6).
- **Body scale:** the viewer's body from `avatarSize`, scaled by the Viewpoint frame (§1, §5): body widths, eye heights, steps.
- **Image scale:** pixels and fraction of the frame, from the projection (§2).

### Framing

For the current view, the agent can say:

- which objects are in frame, cut off (and at which edge), behind the viewer or beyond the far plane;
- where each one is: pixel position, and left, centre or right third of the frame;
- how big each one appears: pixels and fraction of frame height.

To compose a view, it works the projection backwards:

- **Distance for a target size.** For an object of height `size` to appear `p` pixels tall, stand `d = f_px · size / p` away.
- **Orientation without roll.** To look at a target from eye `E`, level the view direction against up and build the axes:

  ```
  f = normalize(target − E)
  r = normalize(f × up)
  c = r × f
  ```

  Then convert the rotation `[r, c, −f]` to an SFRotation. Express it in the Viewpoint's parent frame and write it to the Viewpoint's `orientation` field.
- **Under WALK,** place the eye at `support + h · up` first, then aim.

### Object relations and frames of reference

X3D has no "left". A direction word only means something within a frame of reference, and each frame has an X3D encoding:

| Frame | Whose axes | X3D encoding |
|---|---|---|
| Relative (the viewer's) | the camera: right, up, forward | bound Viewpoint `orientation` in the Viewpoint frame, or the live camera (below) |
| Intrinsic (the object's) | the ground object's own front and up | HAnimHumanoid faces +Z (+X is its left); glTF assets face +Z; the object's `Transform.rotation` |
| Absolute (the world's) | world up, and north in geospatial scenes | +Y of the scene; `GeoOrigin`/`GeoLocation` for geodetic up |

Direction words in the relative frame, with `up` from §1 and `f` the view direction:

```
level = normalize(f − (f·up) up)       view direction flattened onto the ground plane
right = level × up                     left  = −right
behind X = +level (farther from the viewer)
in front of X = −level (toward the viewer)
above = +up                            below = −up
```

Flattening onto the ground plane means a camera that is tilted or rolled never tilts "right". Moving along `right` keeps the depth `z_c` unchanged and increases `u`, so the object really does appear further right in the image.

Which frame to use:

- **Relative, by default,** when the ground object has no front of its own, such as a sphere, a box or a lamp.
- **Stated or asked,** when the ground object has a front (a humanoid, a chair, a car). "To the right of the car" can then mean either frame.

### Worked example: "put that box to the right of the sphere"

Scene: `examples/room_inspection/room.x3d`. Verified live from all four Viewpoints in both X_ITE and X3DOM by `tests/test_live.py`. The Corner and Overlook results are in `tests/test_relations.py`.

1. **Which box.** "That box" means a free-standing object in view. The floor and back wall are `Box` geometry too, but they are supporting and enclosing surfaces, so the box is `Table`. If more than one candidate is in view, ask.
2. **Whose right.** Use the viewer's current perspective: the bound Viewpoint, or the live camera if the user has navigated.
3. **Resolve "right"** with `right = level × up` for that perspective.
4. **Place the box.** New centre = sphere centre + `right · (sphere radius + the box's half-width along right + gap)`. Keep the box's height on its support, since gravity still applies to it.
5. **Apply the move.** Convert the new centre into the Table's parent frame and set `Table.translation`. Do this either live, through the browser API, or in the document with x3d_mcp's `modify_x3d_node`.
6. **Check it.** Imagine the new view, capture it, and confirm the box is now right of the sphere in the image.

| Viewpoint | "Right" in world coordinates | New `Table.translation` | Imagined u of sphere, then box | Seen in the capture |
|---|---|---|---|---|
| `Entry` (0 1.6 4, looking −Z) | +X | `−0.55 0.375 −1` | 379, then 544 | box right of the sphere |
| `Side` (2.9 1.6 −1, looking −X) | −Z | `−1.5 0.375 −1.75` | 640, then 788 | box right of the sphere |

The same sentence moves the box in different directions depending on the perspective. That difference is the whole point of taking the viewer's perspective.

### The live viewer

After the user navigates, the perspective is the live camera, not the authored Viewpoint. Two ways to read it, both verified by `tests/test_live.py` to agree with the imagined eye to within 1 cm:

- **Portable X3D, used for X_ITE:** a `ProximitySensor` enclosing the world reports `position_changed` and `orientation_changed`.
- **X3DOM:** `runtime.viewMatrix().inverse()`, the approach the x3dom-spikes' adapter uses.

## 4. Up and gravity

### Normative rules

- 23.3.1: *"Navigation types … that require a definition of a down vector … shall use the negative Y-axis of the coordinate system of the currently bound X3DViewpointNode node."*
- 23.3.1: *"The orientation field of the X3DViewpointNode node does not affect the definition of the down or up vectors."* Tilting or rolling the camera does not tilt the world.
- 23.4.4 (WALK): *"It is strongly recommended that WALK navigation define the up vector in the +Y direction and provide some form of terrain following and gravity in order to produce a walking or driving experience."*
- 23.4.4 (FLY): *"FLY navigation is similar to WALK except that terrain following and gravity may be disabled or ignored."*

**Gravity attracts along −up.** Up is +Y of the bound Viewpoint's frame `V`.

### Behavior by `NavigationInfo.type`

| `type` | Gravity along −up | Terrain following | Collision |
|---|---|---|---|
| `WALK` | yes | eye kept `h` above terrain; the viewer can move over objects up to `k` tall | *"shall strictly support collision detection"* |
| `FLY` | may be disabled or ignored | may be disabled or ignored | strictly supported |
| `NONE` | no user navigation | none | strictly supported |
| `EXAMINE`, `ANY` | no | no | *"may temporarily disable collision detection during navigation, but shall not disable it during normal world execution"* |
| `LOOKAT`, `EXPLORE` | no | no | not stated; the skill treats them like `EXAMINE` |

WALK physics in one line: gravity pulls the avatar along −up until it finds support. The eye then rides `h` above that support. Ledges up to `k` can be stepped over, and geometry closer than `r` blocks movement.

X3D gives WALK gravity a direction but no magnitude, so fall speed is up to the browser. The skill models it as "settle to support" rather than as an acceleration.

### Other up and gravity evidence

These fields are not normative for navigation. The skill uses them to cross-check up.

| Node.field | Default | Meaning | Check the skill applies |
|---|---|---|---|
| `RigidBodyCollection.gravity` | `0 −9.8 0` (m/s²) | gravity for rigid-body physics | `normalize(gravity)` should equal `−up` |
| `ForcePhysicsModel.force` | `0 −9.8 0` | constant force on particles; the default is Earth's gravity | same as above |
| `GeoOrigin.rotateYUp` | `FALSE` | `FALSE`: local up is relative to the planet surface. `TRUE`: local up is aligned with Y, which *"allows proper operation of NavigationInfo modes FLY, WALK"* | geospatial scenes: up is the ellipsoid normal, not +Y |
| root `Transform rotation='1 0 0 −1.5708'` | — | common fix when importing Z-up content (CAD, BIM, GIS, Blender) | report it; if it is missing and floors are perpendicular to Z, suggest it |

### Which way objects face

"In front of X" depends on which way X faces. These are the conventions:

| Node or content | Front and up |
|---|---|
| `Viewpoint` | looks along local −Z, local +Y up |
| `HAnimHumanoid` | stands at the origin, +Y up, faces +Z; +X is the humanoid's left (ISO/IEC 19774) |
| glTF loaded through `Inline` | +Y up, front faces +Z, meters (glTF 2.0) |
| `Billboard` | turns local +Z toward the viewer around `axisOfRotation` (default `0 1 0`). With `0 0 0`, it keeps local Y parallel to the viewer's Y |

## 5. Human units (the avatar's body)

`NavigationInfo.avatarSize`, default `[0.25 1.6 0.75]` (23.4.4):

- `[0]`: *"the allowable distance between the user's position and any collision geometry"*. This is the collision radius `r`, and it also sets the near plane.
- `[1]`: *"the height above the terrain at which the X3D browser shall maintain the viewer"*. This is eye height `h`, not stature. Under WALK it overrides the authored Viewpoint height (§1).
- `[2]`: *"the height of the tallest object over which the viewer can move"*. This is step height `k`.

Other NavigationInfo fields:

- `speed`: default 1.0 m/s.
- `type`: default `"EXAMINE" "ANY"`.
- `headlight`: default `TRUE`.
- `transitionType`: default `"LINEAR"`; other values are `"TELEPORT"` and `"ANIMATE"`.
- `transitionTime`: default 1.0 s.

An embodied avatar:

- `HAnimHumanoid` with `x3d:hasViewpoints` pointing to `HAnimSite` nodes gives first-person camera mounts.
- Other fields: `skeletalConfiguration` (default `"BASIC"`) and `loa` (default −1).
- Joint positions give stature, shoulder height and reach.

The skill phrases distances in body terms:

| Human term | Definition | With defaults |
|---|---|---|
| body width | `2r` | 0.5 m |
| at eye level | within `h ± 0.15` m | 1.45–1.75 m |
| steppable | rise of `k` or less | 0.75 m |
| passable gap | at least `2r` wide | 0.5 m |
| time to reach | distance / speed | 1 s per meter |

Two caveats about the default body:

- X3D defines no head clearance above the eye. The skill's conservative body capsule takes a `headroom` parameter, which X3D does not supply.
- The default `k = 0.75` m is knee-high, about four stair risers (0.15–0.19 m each). Presets for realistic human bodies should lower it and output the result as a `NavigationInfo` node.

## 6. Scale (meters)

The `unit` statement in `<head>` (X3D 3.3 and later):

```xml
<head><unit category='length' name='centimeters' conversionFactor='0.01'/></head>
```

- `x3d:category` takes one of `angle`, `force`, `length` or `mass`. The ontology's `x3d:unitCategoryChoices` enumeration is closed.
- `x3d:conversionFactor` is an SFDouble, default 1.0. It *"converts new base unit to default base unit"*. The default base units are meters, radians, kilograms and newtons.
- Units are declared per file. Content loaded through `Inline` carries its own `head`, so the skill tracks units per file.

Other sources of scale:

- **`Transform` composition:** `P' = T · C · R · SR · S · −SR · −C · P`. The same transform fields appear on `HAnimHumanoid`, `HAnimJoint`, `CADPart`, `GeoTransform` and `EspduTransform`.
- **`X3DBoundedObject.bboxSize`:** the default `−1 −1 −1` means the author did not provide a box, so the skill computes one from the geometry.
- **Primitive defaults (local units):** `Box size 2 2 2`, `Sphere radius 1`, `Cylinder radius 1 height 2`, `Cone bottomRadius 1 height 2`.
- **`LOD.range`:** given in the LOD's local units, so it scales with the LOD's ancestors.
- **No `unit` statement:** the skill infers a factor from human-scale priors (door, ceiling, table, seat and stair heights) and reports it as inferred. It never silently rescales.

## 7. Visibility

### View frustum

- Apex, axis and field of view come from the table in §1; the projection is in §2.
- 23.3.1: *"the smaller of display width or display height determines which angle equals the fieldOfView."* The skill takes the view size as a parameter; the default is 1280×720.
- `OrthoViewpoint.fieldOfView` defaults to `−1 −1 1 1` (minimum and maximum x and y extents).
- **Near plane.** 23.3.1: *"A default value of −1 for nearDistance or farDistance means that the field has no effect on currently active view-frustum boundaries."* 23.4.4: *"It is recommended that the near clipping plane be set to one-half of the collision radius as specified in the avatarSize field."*
- **Far plane.** Use `farDistance` if it is not −1; otherwise `visibilityLimit`, where `0.0` means infinite. `farDistance` must be greater than the near distance.

### How collision protects against near-plane clipping

Collision and the near plane are linked through `avatarSize[0]`:

- Collision keeps every geometry point at distance `d ≥ r` from the eye.
- A point at angle `φ` from the view axis has depth `d·cos φ`.
- The point is near-clipped only if `d·cos φ < r/2`. With `d ≥ r`, that requires `φ > 60°`.

So in `WALK`, `FLY` and `NONE`, geometry the avatar can legally approach is never near-clipped, provided the frustum's corner half-angle stays under 60°. The default 0.7854 rad on a 16:9 display has a corner half-angle of about 40°.

The skill reports `NEAR_CLIPPED` as its own reason in two cases:

- a wide field of view, where the corner half-angle is over 60°;
- `EXAMINE` or `ANY` navigation, where collision may be off during navigation.

### Is the object rendered at all?

- `Switch.whichChoice`: default −1, meaning no child is rendered.
- `LOD`: the active level is chosen by `range` and `center` at the eye distance.
- `visible`: X3D 4 field, default `TRUE`. It appears on `X3DBoundedObject`, `X3DShapeNode` and `X3DLayerNode`.

### What blocks the line of sight

- `Material.transparency` and `PhysicalMaterial.transparency`: default 0; 1 means clear.
- `Appearance.alphaMode`: default `"AUTO"`.
- `solid`: when `TRUE`, back faces are culled and do not occlude. It defaults to `TRUE` for `Box`, `Cone`, `Cylinder`, `ElevationGrid`, `Extrusion` and the composed geometry nodes such as `IndexedFaceSet`. It defaults to `FALSE` for 2D primitives such as `Disk2D` and `Rectangle2D`.
- Line and point geometry does not occlude.

### Atmosphere

- `Fog.visibilityRange`: default 0, which means fog is off.
- `Fog.fogType`: default `"LINEAR"`.

### Checking in a live browser

- `VisibilitySensor` (`center`, `size`) reports frustum visibility of a box. It does not guarantee occlusion.
- `ProximitySensor` reports the viewer's actual position and orientation.

### Reason codes

The skill reports why an object is or is not visible with one of these codes: `NOT_RENDERED`, `OUT_OF_FRUSTUM`, `NEAR_CLIPPED`, `BEYOND_FAR`, `FOGGED`, `OCCLUDED_BY(<DEF>)`, `TOO_SMALL`, `VISIBLE`.

## 8. Collision

`Collision` node (23.4.2). In the ontology it is a subclass of both `x3d:X3DGroupingNode` and `x3d:X3DSensorNode`.

- `enabled`: default `TRUE`.
- `proxy` (`x3d:hasProxy`): *"used as a substitute for the Collision node's children during collision detection"*. The proxy is not rendered.
- `isActive` and `collideTime`: outputs.
- What collides by default: *"all geometric nodes in the scene are collidable with the viewer except IndexedLineSet and PointSet."*
- Which navigation types require collision: see the table in §4.

The avatar X3D defines is an eye point with three properties:

- a collision distance `r`;
- terrain following at height `h` along −up;
- a step allowance `k`.

X3D does not define a full body volume. The skill therefore offers two modes:

- **`x3d` mode** implements only the normative rules above.
- **`body` mode** uses a conservative capsule of radius `r`, from `k` up to `h + headroom`.

It reports cases where the two modes disagree, for example a beam a browser lets you walk under but a person would hit.

Seeing and passing are independent:

| Case | Can see through? | Can pass through? |
|---|---|---|
| glass (transparent, collidable) | yes | no |
| curtain inside `Collision enabled='false'` | no | yes |
| `proxy`-only blocker | nothing to see | no |
| `visible='false'` geometry | no | the spec does not say (see §11) |

For object-to-object physics, the Rigid Body Physics component provides `CollidableShape`, `CollidableOffset`, `CollisionCollection`, `CollisionSpace`, `CollisionSensor`, and `RigidBodyCollection.gravity`.

## 9. Binding

- `X3DBindableNode` provides `set_bind`, `isBound` and `bindTime`. Only one node of each bindable type is bound at a time.
- Binding a Viewpoint that has a `navigationInfo` field (X3D 4) brings its body along with it.
- In a live browser, a bind takes effect on the next frame. Read the bound Viewpoint only after a frame has passed.
- `ViewpointGroup` fields: `center`, `size` and `displayed` (default `TRUE`), plus `description` and `retainUserOffsets`.

## 10. Linking to the X3D Ontology

[`ontology/x3d_grounding.ttl`](../ontology/x3d_grounding.ttl) links each agent concept to X3D Ontology 4.1 terms.

How the X3D Ontology models terms:

- Each node is a class, such as `x3d:Viewpoint` or `x3d:NavigationInfo`. Each class is a subclass of its abstract type, such as `x3d:X3DViewpointNode`, `x3d:X3DBindableNode` or `x3d:X3DBoundedObject`.
- Simple-valued fields are **global** datatype properties, such as `x3d:avatarSize` or `x3d:fieldOfView`. The domain lists every node that has the field, and defaults are annotations such as `x3d:avatarSizeDefault ( 0.25 1.6 0.75 )`.
- Node-valued fields are object properties named `x3d:has<Field>`, such as `x3d:hasChildren`, `x3d:hasProxy` and `x3d:hasViewpoints`.
- The `unit` statement is `x3d:unit`, a subclass of `x3d:X3DStatement`, with `x3d:category` and `x3d:conversionFactor`.

Because the field properties are global, the same IRI is declared several times with different ranges and defaults:

- `x3d:fieldOfView` is SFFloat on `Viewpoint`, MFFloat on `OrthoViewpoint`, and SFVec4f on `TextureProjectorParallel`.
- `x3d:solid` defaults to true on `Box` and false on `Disk2D`.

The ontology also has one inconsistency that matters here. `x3d:navigationInfo`, the link from a Viewpoint to its body, is declared as a datatype property, but its range is the class `x3d:NavigationInfo`. By the ontology's own naming pattern it should be an object property called `x3d:hasNavigationInfo`.

So the grounding:

- links each concept to a **(node class, field) pair**, never to a bare field IRI;
- uses annotation properties, not `owl:equivalentClass`. The agent's concepts are computed from X3D nodes; they are not X3D node types.
- takes per-node defaults from x3d_mcp's `describe_node` (X3DUOM 4.1). `tests/test_x3d_grounding.py` checks every grounded node, field and default against that output.

```turtle
:TraversableSpace :groundedIn
    [ :x3dNode x3d:NavigationInfo ; :x3dField x3d:avatarSize ; :fieldIndex 1 ;
      :x3dDefault "1.6" ; :quantityUnit unit:M ; :scaledBy :BoundViewpointFrame ;
      :rule "The browser keeps the viewer this far above the terrain (23.4.4)." ] .
```

Whether an `x3d:` term exists is for x3d_mcp to check (`describe_ontology_term`). Its bundled ontology is still 4.0, so it needs the 4.1 file ([ARCHITECTURE.md](ARCHITECTURE.md#ontology-version)).

## 11. Open questions

These need a check against the spec text before they are coded.

1. **`unit` statements and spec defaults.** Under a `length` `unit` statement, is an omitted `avatarSize` still `0.25 1.6 0.75` meters, or is it in the declared units? The implementation records which interpretation it used.
2. **`visible='false'` and collision.** The Navigation component does not say. The skill currently treats invisible geometry as collidable, and this is configurable.
3. **`nearDistance` and `farDistance` scaling.** The skill assumes these are in the Viewpoint's local units and therefore scaled by `V`.
4. **`LOOKAT` and `EXPLORE` collision** requirements are not stated.
5. **Initial binding** of Viewpoint and NavigationInfo nodes inside `Inline` content.
