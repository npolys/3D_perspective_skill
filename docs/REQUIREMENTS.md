# Requirements

What the skill must do, as stated during planning, with where each requirement is handled and its current status.

| # | Requirement | Where | Status |
|---|---|---|---|
| R1 | Ground the agent's concepts (up and coordinate systems, human units, meter scale, visibility, collision) to X3D nodes and values | [X3D_MAPPINGS.md](X3D_MAPPINGS.md) §1, §4–§8; `ontology/x3d_grounding.ttl` | documented; groundings tested against `describe_node` |
| R2 | WALK has gravity (along −up) and collision detection; `avatarSize` sets the collision distance and the near clipping plane (`avatarSize[0] / 2`) | X3D_MAPPINGS.md §1, §4, §7 | documented; gravity verified in X_ITE |
| R3 | Account for how the Viewpoint and `avatarSize` couple, and for their spec defaults | X3D_MAPPINGS.md §1; `perspective.py` | implemented. Verified: X_ITE settles a WALK eye on bind; X3DOM 1.8.3 keeps the authored eye until the user moves |
| R4 | Use X3D 4.1 | the ontology namespace; emitted documents; spec quotes checked in the 4.1 draft | done |
| R5 | x3d_mcp handles X3D correctness: schema and DTD, ontology terms, node definitions, rendering | [ARCHITECTURE.md](ARCHITECTURE.md) | done; the hosted endpoint is used as an MCP endpoint |
| R6 | The agent's perspective is the 2D view of the 3D scene; it can see, imagine and capture the X3DOM or X_ITE rendered view | X3D_MAPPINGS.md §2; `view.py`, `live.py`, `imaging.py`; `see`, `capture` | implemented; verified from four viewpoints in both renderers (`tests/test_live.py`) |
| R7 | The default render size is HD (16:9) for both X3DOM and X_ITE | 1280×720 in `view.py` and `live.py`; [`upstream/x3d_mcp/`](../upstream/x3d_mcp/) | done in the skill; the x3d_mcp patch needs a redeploy |
| R8 | Resolve viewer-relative instructions such as "put that box to the right of the sphere" | X3D_MAPPINGS.md §3; `relations.py`; `resolve`, `place` | implemented; verified from four viewpoints in both renderers |
| R9 | Change the live scene through the X3DOM and X_ITE APIs | ARCHITECTURE.md; `live.py`; `capture --set` | implemented; verified in both (bind, set fields, camera readback) |
| R10 | Understand scale, framing and object relations | X3D_MAPPINGS.md §3; `frame`, `see`, `relate` | implemented |
| R11 | The skill works from several viewpoints in the same scene, with both X3DOM and X_ITE | `tests/test_live.py`: Entry, Side, Corner, Overlook × X_ITE, X3DOM | done: 16 live checks pass |
