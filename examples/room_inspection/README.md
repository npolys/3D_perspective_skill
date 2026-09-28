# Room inspection

`room.x3d` is a small X3D 4.1 scene for checking perspective-taking. It uses meters and +Y up. x3d_mcp's `validate_x3d` and `validate_semantic` report it valid, with no errors.

| Object (DEF) | Geometry | Where |
|---|---|---|
| `Floor` | Box 6 × 0.1 × 8 m | top at y = 0; extends under the entry |
| `BackWall` | Box 6 × 3 × 0.1 m | z = −3 |
| `Table` | red Box 1.2 × 0.75 × 0.8 m | on the floor at the origin |
| `Lamp` | blue Sphere, radius 0.25 m | floating at (−1.5, 1.2, −1) |
| `Plant` | green Cylinder, radius 0.2 m, height 1 m | on the floor at (1.5, 0, −0.5) |

The NavigationInfo is WALK with the default `avatarSize` `0.25 1.6 0.75`.

| Viewpoint | Position | Looking | Why it's there |
|---|---|---|---|
| `Entry` | 0 1.6 4 | along −Z | the default view into the room |
| `Side` | 2.9 1.6 −1 | along −X | "right" is −Z here |
| `Corner` | −2.5 1.6 2.5 | across the room | a diagonal "right"; the table partly hides the plant |
| `Overlook` | 0 2.8 3.5, pitched down | into the room | X_ITE lowers the eye to 1.6 m under WALK; X3DOM keeps 2.8 m |

Run the example:

```
python examples/room_inspection/example.py
python examples/room_inspection/example.py --live
```

For each Viewpoint and renderer, it prints where the table and lamp land, and what "put that box to the right of the sphere" does. With `--live` it also verifies every view in X_ITE and X3DOM and keeps the captures in `captures/`.
