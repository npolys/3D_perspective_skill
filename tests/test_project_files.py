"""Checks that the project files parse and agree with each other."""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from snapshot_defaults import NODE_TYPES, OUT_PATH  # noqa: E402

DEFAULTS = json.loads(OUT_PATH.read_text(encoding="utf-8"))
TURTLE_FILES = sorted((ROOT / "ontology").glob("*.ttl"))


@pytest.mark.parametrize("path", TURTLE_FILES, ids=lambda p: p.name)
def test_turtle_parses(path):
    rdflib = pytest.importorskip("rdflib")
    rdflib.Graph().parse(path, format="turtle")


def test_skill_header():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    header = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    assert header, "SKILL.md must start with a --- YAML header"
    fields = dict(line.split(":", 1) for line in header.group(1).splitlines())
    name, description = fields["name"].strip(), fields["description"].strip()
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64
    assert 0 < len(description) <= 1024


def test_mcp_config_points_at_x3d_endpoint():
    config = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    assert config["mcpServers"]["x3d"]["url"].endswith("/mcp")


def test_defaults_snapshot_is_the_package_data():
    from x3d_perspective import x3d_loader
    assert x3d_loader.default("Viewpoint", "position") == DEFAULTS["nodes"]["Viewpoint"]["fields"]["position"]["default"]


def test_defaults_snapshot_covers_analyzer_nodes():
    assert list(DEFAULTS["nodes"]) == NODE_TYPES


# Defaults quoted in docs/X3D_MAPPINGS.md, checked against the describe_node snapshot.
@pytest.mark.parametrize("node, field, default", [
    ("Viewpoint", "position", "0 0 10"),
    ("Viewpoint", "orientation", "0 0 1 0"),
    ("Viewpoint", "fieldOfView", "0.7854"),
    ("Viewpoint", "nearDistance", "-1"),
    ("Viewpoint", "farDistance", "-1"),
    ("NavigationInfo", "avatarSize", "0.25 1.6 0.75"),
    ("NavigationInfo", "speed", "1"),
    ("NavigationInfo", "visibilityLimit", "0"),
    ("NavigationInfo", "type", '"EXAMINE" "ANY"'),
    ("NavigationInfo", "headlight", "true"),
    ("Background", "skyColor", "0 0 0"),
    ("Collision", "enabled", "true"),
    ("Transform", "visible", "true"),
    ("Switch", "whichChoice", "-1"),
    ("Material", "transparency", "0"),
    ("Fog", "visibilityRange", "0"),
    ("Box", "size", "2 2 2"),
    ("Box", "solid", "true"),
    ("Billboard", "axisOfRotation", "0 1 0"),
    ("RigidBodyCollection", "gravity", "0 -9.8 0"),
    ("GeoOrigin", "rotateYUp", "false"),
])
def test_grounding_defaults_match_snapshot(node, field, default):
    assert DEFAULTS["nodes"][node]["fields"][field]["default"] == default
