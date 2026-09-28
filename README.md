# 3D Perspective Agent Skill v7

An agent skill for taking the user's perspective on an X3D scene: the 2D view that X_ITE or X3DOM renders from the bound Viewpoint.

The agent can:

- imagine that view, capture it, and see it;
- understand scale, framing and object relations from it;
- act on viewer-relative instructions such as "put that box to the right of the sphere", live or in the document.

Everything is tied to X3D 4.1 nodes and fields: up and gravity, units and meter scale, the viewer's body (`avatarSize`), what is visible, and what collides.

It works alongside the Web3D Consortium's [x3d_mcp](https://github.com/Web3DConsortium/x3d_mcp) server. That server owns X3D correctness: validation, node definitions, ontology terms and rendering. This repo owns the perspective.

- [SKILL.md](SKILL.md): the skill Claude loads.
- [docs/X3D_MAPPINGS.md](docs/X3D_MAPPINGS.md): the rules, mapped to X3D nodes, fields and defaults, and checked against X_ITE renders.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): the split with x3d_mcp, capturing and changing the live view, the hosted endpoint's limits, and the phases.
- [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md): what was asked for, and its status.
- [examples/room_inspection/room.x3d](examples/room_inspection/room.x3d): the test room used in the checks.

## Setup

```
python -m venv .venv
.venv\Scripts\python -m pip install -e .[dev,live]
.venv\Scripts\python -m playwright install chromium
.venv\Scripts\python -m pytest            # offline tests
.venv\Scripts\python -m pytest --live     # also drive X_ITE and X3DOM (needs network for the renderers' scripts)
```

Try it on the test room:

```
.venv\Scripts\x3d-perspective see examples\room_inspection\room.x3d --viewpoint Side
.venv\Scripts\x3d-perspective place examples\room_inspection\room.x3d Table "right of" Lamp --viewpoint Side
.venv\Scripts\x3d-perspective capture examples\room_inspection\room.x3d --renderer x3dom --viewpoint Side --set Table.translation="-1.5 0.375 -1.75" --out side.png
```

[.mcp.json](.mcp.json) connects Claude Code to the hosted x3d_mcp endpoint at `https://x3d-mcp.onrender.com/mcp`.

To install the skill, copy or link this folder into `~/.claude/skills/` under the name `x3d-perspective`, which matches the skill's name.

## Status

Phases 0–3 are done. The `x3d-perspective` commands (`frame`, `see`, `resolve`, `relate`, `place`, `capture`) and the live driver work in both X_ITE and X3DOM. They're verified from four viewpoints of the test room ([docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)).

Still to come: collision paths (Phase 4), an MCP wrapper (Phase 5) and SHACL export (Phase 6).

Proposed changes to x3d_mcp, as a patch ready to apply, are in [upstream/x3d_mcp/](upstream/x3d_mcp/).
