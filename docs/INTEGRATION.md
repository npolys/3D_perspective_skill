# Integrating x3d-perspective into other applications

This document shows how to use x3d-perspective from other Python applications, from command-line tools, and as a Claude Agent Skill. It also covers common integration patterns and notes on security and runtime requirements.

## Install

From PyPI (when published):

```
pip install x3d-perspective
```

To get live capture support (Playwright + Pillow):

```
pip install "x3d-perspective[live]"
python -m playwright install chromium
```

To work from a checked-out copy (editable):

```
pip install -e .[dev,live]
python -m playwright install chromium
```

## Use from Python (recommended)

The package exports a small, focused API for loading scenes, imagining views, placing objects, and driving a live renderer.

```python
import x3d_perspective as xp

# Load a scene
scene = xp.load("room.x3d")

# Take a perspective from a named Viewpoint (renderer: "spec", "x_ite", "x3dom")
p = xp.from_viewpoint(scene, "Side", renderer="x3dom")

# Imagine the view at 1280x720
view = xp.see(scene, p, size=(1280, 720))

# Resolve or plan a placement
plan = xp.place(scene, p, "Table", "right of", "Lamp")
print(plan["set_field"])  # applyable translation value

# Drive the live view (needs the `live` extra)
from x3d_perspective.live import LiveView
with LiveView("room.x3d", renderer="x3dom") as live:
    live.bind("Side")
    live.set_field("Table", "translation", plan["set_field"]["value"])
    png = live.capture("after.png")
```

Notes:
- All distances are in meters after the scene's `unit` statement.
- Field defaults come from the X3DUOM snapshot included in the package — see `src/x3d_perspective/data/x3d_defaults.json`.

## Use from the command line

The `x3d-perspective` command exposes the most common workflows and prints JSON on stdout. Example:

```
x3d-perspective see room.x3d --viewpoint Side --renderer x3dom
x3d-perspective capture room.x3d --renderer x3dom --viewpoint Side --out side.png
x3d-perspective place room.x3d Table "right of" Lamp --viewpoint Side
```

Call the CLI from other applications and parse its JSON output if you prefer to keep the skill as an external tool (subprocess, job runner, or container).

## Use as a Claude Agent Skill

To use this repository as a Claude skill:

1. Install the package (editable mode is useful during development):

   ```
   pip install -e .[live]
   python -m playwright install chromium
   ```

2. Put (or link) this repository into `~/.claude/skills/x3d-perspective` so the folder name matches the skill name in `SKILL.md`.
3. Claude will load the skill and call into it according to SKILL.md. The skill leaves validation and document edits to an MCP server (`x3d_mcp`) as described in ARCHITECTURE.md.

## Integration patterns

- Embedding: import the package in your Python app and call `load`, `from_viewpoint`, `see`, `place`. This is the most efficient integration.
- Service: run a small HTTP wrapper that accepts scenes and commands, calls x3d-perspective, and returns JSON responses. Keep the live capture step isolated to workers with Playwright and Chromium installed.
- CLI bridge: invoke `x3d-perspective` as a subprocess and parse its JSON output. This is convenient when integrating from non-Python environments.

## Security and sandboxing

- Live capture launches a headless Chromium. By default the package avoids adding `--no-sandbox` to Chromium's command line. If you need to enable `--no-sandbox` (some CI environments), pass the CLI `--no-sandbox` flag or use `LiveView(..., allow_no_sandbox=True)`.
- Running untrusted scenes in a browser can be risky. Run live captures in isolated containers, VMs or ephemeral job runners, and avoid running captures on hosts with sensitive data.
- The live pages load renderer scripts from CDNs for convenience. For high-assurance environments, host renderer scripts locally and pass them via the LiveView `launch_args` or adapt the HTML templates in `live.py`.

## Dependencies and runtime

- Core: Python 3.10+, NumPy, lxml.
- Live: Playwright and Chromium, Pillow.
- Development: pytest, ruff, rdflib, build, twine.

## Examples and tests

- Examples: `examples/room_inspection` includes an example scene and a usage script.
- Tests: `pytest` runs offline tests. `pytest --live` runs live tests and requires the `live` extra and network access to the renderer CDNs.

## Contact and support

Open an issue or PR on the repository: https://github.com/npolys/3D_perspective_skill
