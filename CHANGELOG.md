# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org).

## Unreleased


## [7.0.1] - 2026-09-28

- Defensive fix: handle degenerate footprint extents in view._footprint to avoid crashes when computing OUT_OF_FRUSTUM.
- LiveView security: avoid passing --no-sandbox by default; expose allow_no_sandbox and CLI --no-sandbox flag. Document sandboxing guidance in README.
- Added unit test to cover the footprint/extent degenerate case.

## [7.0.0] - 2026-09-28

The first published release of `x3d-perspective`. Earlier versions (up to v6) lived in the same repository as an ontology and planning skeleton.

### Added

- **The Agent Skill (`SKILL.md`)** for taking the user's perspective on an X3D scene: imagine, capture and see the rendered 2D view; scale, framing and object relations; viewer-relative instructions.
- **The `x3d_perspective` package and `x3d-perspective` command:** `frame`, `see`, `resolve`, `relate`, `place`, `capture`, `verify`.
- **The X3D 4.1 rules** in `docs/X3D_MAPPINGS.md`, each with its spec clause:
  - the bound Viewpoint and NavigationInfo;
  - WALK gravity along −up, with `avatarSize` as collision distance, eye height and step;
  - the near plane at `avatarSize[0] / 2`;
  - Viewpoint scaling of the body;
  - projection with `fieldOfView` across the smaller side;
  - viewer-relative directions;
  - visibility reason codes.
- **Live drivers for X_ITE 16.4.1 and X3DOM 1.8.3** (`x3d_perspective.live`): bind Viewpoints, set fields, read the live camera, capture. Runs headless with software GL.
- **Verification (`x3d_perspective.verify`, `x3d-perspective verify`):** compares the imagined view with both renderers for any scene.
- **Measured renderer behaviour:** X_ITE settles a WALK eye onto support when a Viewpoint is bound; X3DOM keeps the authored eye until the user moves.
- **Field defaults from x3d_mcp's `describe_node`** (X3DUOM 4.1), shipped as package data, with `scripts/snapshot_defaults.py` to refresh them.
- **An ontology of the agent's concepts** (`ontology/`), linked to X3D Ontology 4.1 terms in `x3d_grounding.ttl`, with spatial relations that name their perspective.
- **The test room** `examples/room_inspection/room.x3d`, with four Viewpoints, plus an example script.
- **Tests:** 91 offline and 20 live.
- **Tooling:** ruff linting, GitHub Actions CI, and the CLI, API and testing docs.
- **A proposed x3d_mcp patch** (`upstream/x3d_mcp/`): HD default render size, and an `mcp<2` pin.

### Changed

- The package is renamed from `perspective-agent` to `x3d-perspective` (import `x3d_perspective`).
- The license is now the Web3D Consortium Open-Source License for Models and Software.

### Removed

- The v6 placeholder modules (`api`, `perception`, `navigation`, `planning`, `world_builder`, `worldmodel`).
- The empty JSON schemas, SHACL file and mapping contracts. Their roles are now filled by `docs/CLI.md`, `ontology/x3d_grounding.ttl` and the defaults snapshot.

[7.0.0]: https://github.com/npolys/3D_perspective_skill/releases/tag/v7.0.0
