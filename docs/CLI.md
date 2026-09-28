# Command line: `x3d-perspective`

Every command takes an X3D XML (`.x3d`) scene and prints one JSON document to standard output. Lengths are in meters (after the scene's `unit` statement) and positions in the image are pixels, measured from the top-left corner.

```
x3d-perspective [--version] COMMAND SCENE [options]
```

## Common options

| Option | Commands | Meaning |
|---|---|---|
| `--viewpoint DEF` | all except `frame` and `verify` | the Viewpoint to take. Default: the one bound when the scene loads (the first in the file), or the X3D default camera if there is none |
| `--renderer spec\|x_ite\|x3dom` | all except `frame` and `verify` | whose WALK behaviour to imagine. `spec` and `x_ite` settle the eye onto support when a Viewpoint is bound; `x3dom` keeps the authored eye until the user moves. `capture` needs `x_ite` or `x3dom` (default `x_ite`) |
| `--size WxH` | all except `frame` | view size in pixels. Default `1280x720` (HD) |
| `--no-sandbox` | `capture`, `verify` | When present, Chromium is launched with `--no-sandbox`. This is unsafe on multi-tenant hosts; prefer running captures in an isolated container or VM. The default is to avoid `--no-sandbox`. |

## `frame`: the scene's frame

```
x3d-perspective frame room.x3d
```

| Field | Meaning |
|---|---|
| `units` | `meters_per_unit` and where it came from (`unit statement '…'` or `default (meters)`) |
| `up`, `gravity` | +Y and −Y of the initially bound Viewpoint's parent frame |
| `up_evidence` | why: the Viewpoint frame; a root `Transform` that rotates Z-up content to Y-up |
| `extent_m` | `min`, `max` and `size` of all geometry |
| `navigation` | the bound NavigationInfo: `type`, `walk_gravity`, `avatarSize`, `speed`, `headlight`, `visibilityLimit` |
| `background_sky` | the Background `skyColor`, or `null` |
| `viewpoints[]` | `name`, `description`, `authored_eye_m`, `eye_m` (after WALK settling), `falls`, `forward` |
| `objects[]` | `name` (nearest DEF), `geometry`, `size_m`, `center_m`, `structural` (floor, wall or ceiling slab), `rendered`, `movable_by` (the DEF'd Transform to move it) |
| `warnings` | for example Z-up content without a rotation, or physics gravity not along −up |

## `see`: the imagined view

```
x3d-perspective see room.x3d --viewpoint Side --renderer x3dom
```

Top level:

| Field | Meaning |
|---|---|
| `perspective` | the viewer: `eye_m`, `authored_eye_m`, `falls`, `support`, `forward`, `up`, `right`, `field_of_view`, `near_m`, `far_m`, `body_m` (`collision_radius`, `eye_height`, `step_height`), `speed_m_s`, `headlight`, `notes` |
| `size`, `focal_px`, `horizontal_fov_deg` | the frame (`fieldOfView` spans its smaller side) |
| `objects[]` | one entry per object (below) |
| `background_only` | true when no object is visible |
| `reason` | present when the viewer falls: `VIEWER_FALLS: …` |

Each object:

| Field | Meaning |
|---|---|
| `name`, `geometry` | the object (nearest DEF'd ancestor) and its geometry node types |
| `status` | the reason code (below) |
| `pixel_box` | `[u0, v0, u1, v1]` of the part inside the frame |
| `center_px` | where the object's center projects (may lie outside the frame) |
| `cut_off` | frame edges that cut the object: `left`, `top`, `right`, `bottom` |
| `size_px`, `frame_height_fraction`, `third` | apparent size; share of the frame height; `left`, `centre` or `right` third |
| `distance_m`, `depth_m` | from the eye; `nearest` and `center` depth along the view direction |
| `visible_fraction`, `occluded_by` | share of sampled surface with a clear line of sight; what blocks the rest |
| `near_clipped` | part of the object is closer than the near plane |
| `where` | for objects outside the view: `behind the viewer`, `left of the frame`, … |

Reason codes: `VISIBLE`, `NOT_RENDERED` (Switch, `visible='false'`, Collision proxy), `OUT_OF_FRUSTUM`, `BEYOND_FAR`, `FOGGED`, `OCCLUDED_BY(<DEF>)`, `TOO_SMALL`.

## `resolve`: which object a phrase means

```
x3d-perspective resolve room.x3d "that box" --viewpoint Side
```

Returns `match` (a name, or `null`), `candidates` and `reason`.

- A DEF name matches directly.
- Otherwise the geometry word (`box`, `cube`, `sphere`, `ball`, `cylinder`, `cone`) selects free-standing objects, skipping floors, walls and ceilings.
- When several are left, those visible from the Viewpoint are preferred.
- If more than one remains, `match` is `null`: ask the user which one.

## `relate`: relations between two objects

```
x3d-perspective relate room.x3d Table Lamp --viewpoint Entry
```

| Field | Meaning |
|---|---|
| `relations` | those that hold with the objects fully separated: `right of` or `left of`, `in front of` or `behind`, `above` or `below` |
| `center_offsets_m` | the center-to-center offset along each direction |
| `image_u` | the two centers' horizontal pixel positions |

## `place`: the field change for a relation

```
x3d-perspective place room.x3d Table "right of" Lamp --viewpoint Side [--gap 0.1]
```

Relations: `right of`, `left of`, `in front of`, `behind`, `above`, `below`, all from the viewer's perspective.

| Field | Meaning |
|---|---|
| `direction_world` | the world direction the relation names from this Viewpoint |
| `set_field` | `def`, `field` (`translation`), `value`: set it live or with x3d_mcp's `modify_x3d_node` |
| `new_center_m` | the figure's new center |
| `imagined_after` | the figure's and ground's `status`, `pixel_box`, `center_px` and `visible_fraction` after the change |
| `relation_holds`, `overlaps` | the relation holds after the move; objects the moved figure would intersect |
| `notes` | for example `rests on Floor, as it rested on Floor` |

For horizontal relations the figure keeps its height, and if it was resting on something, it rests on whatever is under the new spot. The value is expressed in the frame of the figure's parent, including rotation and scale.

## `capture`: the live view

```
x3d-perspective capture room.x3d --renderer x3dom --viewpoint Side --set Table.translation="-1.5 0.375 -1.75" --out side.png
```

This opens the scene in headless X_ITE or X3DOM (needs the `live` extra), binds the Viewpoint and applies each `--set DEF.field=VALUE` live. It then writes the PNG and compares the capture with the imagined view. `translation` changes are applied to the imagined view too.

| Field | Meaning |
|---|---|
| `camera_m` | the live camera's `position` and `forward` |
| `imagined_eye_m` | where the skill put the eye |
| `objects[]` | per strongly coloured object: `imagined_box`, `seen` (`box` and `shadow_box`), `agrees`, `reason` |
| `notes` | changes the imagined view does not model |
| `page_errors` | JavaScript errors from the page |

## `verify`: check a scene in both renderers

```
x3d-perspective verify room.x3d [--viewpoint DEF ...] [--renderer x_ite|x3dom ...] [--out-dir DIR]
```

For every Viewpoint (or the named ones) in each renderer, this compares the live camera and the coloured objects' boxes with the imagined view.

- **Exit status:** 0 when everything agrees, 1 otherwise.
- **Output:** `ok`, and `results[]` with `viewpoint`, `renderer`, `eye_m`, `camera_m`, `camera_error_m`, `objects`, `problems` and `png`.
- **More:** [TESTING.md](TESTING.md) covers the checks and the tolerances.
