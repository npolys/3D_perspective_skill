"""Snapshot per-node X3D field definitions from the x3d_mcp endpoint.

The analyzer runs offline, so it reads field types and defaults from
src/x3d_perspective/data/x3d_defaults.json (package data) instead of calling
describe_node at run time.
This script refreshes that file from x3d_mcp's describe_node tool, which
serves the X3D Unified Object Model (see docs/ARCHITECTURE.md, "Field defaults").

Standard library only, so it runs before the project's dependencies are installed.

Usage:
    python scripts/snapshot_defaults.py [--url https://x3d-mcp.onrender.com/mcp]
"""

import argparse
import datetime as dt
import json
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://x3d-mcp.onrender.com/mcp"
OUT_PATH = Path(__file__).resolve().parent.parent / "src" / "x3d_perspective" / "data" / "x3d_defaults.json"

# Node types the analyzer reads. Keep in sync with docs/ARCHITECTURE.md.
NODE_TYPES = [
    # Grouping
    "Transform", "Group", "Switch", "LOD", "Billboard", "Collision", "Inline", "CADPart",
    # Shape, geometry and appearance
    "Shape", "Appearance", "Material", "PhysicalMaterial",
    "Box", "Sphere", "Cylinder", "Cone",
    "IndexedFaceSet", "IndexedTriangleSet", "TriangleSet", "IndexedQuadSet", "QuadSet", "ElevationGrid",
    "Extrusion", "Coordinate",
    # Navigation
    "Viewpoint", "OrthoViewpoint", "NavigationInfo",
    # Environment and lighting: what else sets the pixels
    "Fog", "ClipPlane", "Background", "DirectionalLight", "PointLight", "SpotLight",
    # Sensors
    "VisibilitySensor", "ProximitySensor",
    # HAnim
    "HAnimHumanoid", "HAnimJoint", "HAnimSite",
    # Physics
    "RigidBodyCollection", "ForcePhysicsModel",
    # Geospatial
    "GeoOrigin", "GeoViewpoint", "GeoLocation",
]

REQUIRED_FIELD_KEYS = ("type", "accessType", "default")
OPTIONAL_FIELD_KEYS = ("acceptableNodeTypes", "minInclusive", "maxInclusive", "inheritedFrom")


class McpHttpClient:
    """Minimal MCP client for the streamable-HTTP transport (JSON-RPC over POST)."""

    def __init__(self, url, timeout=120):
        self.url = url
        self.timeout = timeout
        self.session_id = None
        self.protocol_version = None
        self._next_id = 0

    def _post(self, message):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        request = urllib.request.Request(
            self.url, data=json.dumps(message).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            self.session_id = response.headers.get("Mcp-Session-Id", self.session_id)
            content_type = response.headers.get("Content-Type", "")
            body = response.read().decode("utf-8")
        if "id" not in message:
            return None  # Notifications get 202 Accepted with no body.
        return _parse_reply(body, content_type, message["id"])

    def request(self, method, params=None):
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            message["params"] = params
        reply = self._post(message)
        if "error" in reply:
            raise RuntimeError(f"{method}: {reply['error']}")
        return reply["result"]

    def initialize(self):
        result = self.request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "x3d-perspective-snapshot", "version": "0.1"},
        })
        self.protocol_version = result.get("protocolVersion")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def list_tools(self):
        return [tool["name"] for tool in self.request("tools/list")["tools"]]

    def call_tool(self, name, arguments):
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(f"{name} failed: {result.get('content')}")
        return result["content"]


def _parse_reply(body, content_type, request_id):
    if "text/event-stream" not in content_type:
        return json.loads(body)
    for line in body.splitlines():
        if line.startswith("data:"):
            message = json.loads(line[len("data:"):].strip())
            if message.get("id") == request_id:
                return message
    raise RuntimeError(f"No reply to request {request_id} in the event stream")


def describe(client, node_type):
    info = json.loads(client.call_tool("describe_node", {"node_type": node_type})[0]["text"])
    if "error" in info:
        raise RuntimeError(f"describe_node({node_type}): {info['error']}")
    fields = {}
    for field in info["fields"]:
        entry = {key: field.get(key) for key in REQUIRED_FIELD_KEYS}
        entry.update({key: field[key] for key in OPTIONAL_FIELD_KEYS if field.get(key)})
        fields[field["name"]] = entry
    return {
        "component": info.get("component"),
        "baseType": info.get("baseType"),
        "containerField": info.get("containerField"),
        "fields": fields,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=DEFAULT_URL, help="x3d_mcp streamable-HTTP endpoint")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    client = McpHttpClient(args.url)
    init = client.initialize()
    snapshot = {
        "source": {
            "endpoint": args.url,
            "server": init.get("serverInfo"),
            "protocolVersion": client.protocol_version,
            "tool": "describe_node",
            "retrieved": dt.date.today().isoformat(),
        },
        "nodes": {node_type: describe(client, node_type) for node_type in NODE_TYPES},
    }
    args.out.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    field_count = sum(len(node["fields"]) for node in snapshot["nodes"].values())
    print(f"Wrote {len(NODE_TYPES)} nodes, {field_count} fields to {args.out}")


if __name__ == "__main__":
    main()
