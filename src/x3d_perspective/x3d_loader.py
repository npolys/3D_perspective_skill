"""Load an X3D XML scene into world-space records the analyzer reasons with.

Positions are converted to meters with the file's length `unit` statement. Field defaults come
from x3d_mcp's describe_node snapshot (contracts/x3d_defaults.json).
"""

import json
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from lxml import etree

from . import geometry, mathx

DEFAULTS_PATH = Path(__file__).resolve().parents[2] / "contracts" / "x3d_defaults.json"

# Nodes whose translation/rotation/scale/scaleOrientation/center fields set a local frame.
TRANSFORMING = {"Transform", "CADPart", "HAnimHumanoid", "HAnimJoint", "HAnimSite", "EspduTransform"}
GROUPING = TRANSFORMING | {
    "Group", "StaticGroup", "Collision", "Switch", "LOD", "Billboard", "Anchor", "CADAssembly",
    "CADLayer", "HAnimSegment", "LayoutGroup", "ScreenGroup", "Viewport", "PickableGroup",
}
VIEWPOINTS = {"Viewpoint", "OrthoViewpoint"}


@cache
def _defaults():
    return json.loads(DEFAULTS_PATH.read_text(encoding="utf-8"))["nodes"]


def default(node_type, name):
    """X3DUOM default for a field, as describe_node reports it."""
    return _defaults().get(node_type, {}).get("fields", {}).get(name, {}).get("default")


def _tag(element):
    tag = element.tag
    return tag.split("}", 1)[1] if isinstance(tag, str) and tag.startswith("{") else tag


def _mfstring(text):
    """Parse an MFString such as '"EXAMINE" "ANY"' into a list."""
    if text is None:
        return []
    parts = text.split('"')
    quoted = [p for p in parts[1::2]]
    return quoted if quoted else text.split()


@dataclass
class NavigationInfo:
    name: str
    type: list
    avatar_size: list
    speed: float
    visibility_limit: float
    headlight: bool
    transition_time: float


@dataclass
class Viewpoint:
    name: str
    kind: str
    description: str
    position: np.ndarray            # local, scene units
    orientation: tuple
    field_of_view: object           # float, or the four extents of an OrthoViewpoint
    near_distance: float
    far_distance: float
    parent_matrix: np.ndarray       # parent frame to root scene units
    navigation_info: NavigationInfo | None = None   # X3D 4 navigationInfo field


@dataclass
class ShapeRecord:
    object: str                     # nearest DEF'd ancestor, or the Shape's own DEF
    geometry: str
    triangles: np.ndarray           # world space, meters
    diffuse_color: tuple | None
    transparency: float
    solid: bool
    rendered: bool
    collidable: bool
    mover: str | None               # DEF of the nearest ancestor Transform, the node to move
    mover_parent_matrix: np.ndarray | None
    mover_translation: np.ndarray | None


@dataclass
class Scene:
    path: Path
    unit: float                     # meters per scene length unit
    unit_source: str
    viewpoints: list = field(default_factory=list)
    navigation_infos: list = field(default_factory=list)
    shapes: list = field(default_factory=list)
    background_sky: tuple | None = None
    fog_range: float = 0.0
    root_rotations: list = field(default_factory=list)   # (DEF, SFRotation) of root-level Transforms
    physics_gravity: list = field(default_factory=list)
    geospatial: bool = False
    notes: list = field(default_factory=list)

    def viewpoint(self, name=None):
        """A Viewpoint by DEF name or description; the initially bound one when name is None."""
        if not self.viewpoints:
            return None
        if name is None:
            return self.viewpoints[0]
        for vp in self.viewpoints:
            if name in (vp.name, vp.description):
                return vp
        raise KeyError(f"no Viewpoint named {name!r}; have {[vp.name for vp in self.viewpoints]}")

    def bound_navigation_info(self, viewpoint=None):
        if viewpoint is not None and viewpoint.navigation_info is not None:
            return viewpoint.navigation_info
        return self.navigation_infos[0] if self.navigation_infos else _navigation_info(None, "default")

    def objects(self):
        """Object name -> list of its shapes, in document order."""
        grouped = {}
        for shape in self.shapes:
            grouped.setdefault(shape.object, []).append(shape)
        return grouped

    def triangles(self, rendered=None, collidable=None, exclude=()):
        """All triangles with per-triangle owner names and solid flags, filtered."""
        tris, owners, solid = [], [], []
        for shape in self.shapes:
            if shape.object in exclude or len(shape.triangles) == 0:
                continue
            if rendered is not None and shape.rendered != rendered:
                continue
            if collidable is not None and shape.collidable != collidable:
                continue
            tris.append(shape.triangles)
            owners += [shape.object] * len(shape.triangles)
            solid.append(np.full(len(shape.triangles), shape.solid))
        if not tris:
            return np.zeros((0, 3, 3)), [], np.zeros(0, dtype=bool)
        return np.concatenate(tris), owners, np.concatenate(solid)


def _field(element, node_type, name):
    value = element.get(name)
    return value if value is not None else default(node_type, name)


def _floats(element, node_type, name):
    value = _field(element, node_type, name)
    return mathx.floats(value) if value else []


def _bool(element, node_type, name):
    return (_field(element, node_type, name) or "false").strip().lower() == "true"


def _navigation_info(element, name):
    t = "NavigationInfo"
    get = (lambda f: _field(element, t, f)) if element is not None else (lambda f: default(t, f))
    return NavigationInfo(
        name=name, type=_mfstring(get("type")), avatar_size=mathx.floats(get("avatarSize")),
        speed=float(get("speed")), visibility_limit=float(get("visibilityLimit")),
        headlight=(get("headlight") or "true").lower() == "true", transition_time=float(get("transitionTime")),
    )


def _unit(root):
    for unit in root.iter("unit"):
        if unit.get("category") == "length":
            return float(unit.get("conversionFactor", "1")), f"unit statement '{unit.get('name', '')}'"
    return 1.0, "default (meters)"


def _geometry(element, node_type):
    g = node_type
    if g == "Box":
        return geometry.box(_floats(element, g, "size"))
    if g == "Sphere":
        return geometry.sphere(float(_field(element, g, "radius")))
    if g == "Cylinder":
        return geometry.cylinder(float(_field(element, g, "radius")), float(_field(element, g, "height")),
                                 _bool(element, g, "bottom"), _bool(element, g, "top"), _bool(element, g, "side"))
    if g == "Cone":
        return geometry.cone(float(_field(element, g, "bottomRadius")), float(_field(element, g, "height")),
                             _bool(element, g, "bottom"), _bool(element, g, "side"))
    coord = next((c for c in element if _tag(c) == "Coordinate"), None)
    points = mathx.floats(coord.get("point", "")) if coord is not None else []
    ccw = _bool(element, g, "ccw") if default(g, "ccw") is not None else True
    if g == "IndexedFaceSet":
        return geometry.polygons(points, [int(i) for i in mathx.floats(element.get("coordIndex", ""))], ccw)
    if g in ("IndexedTriangleSet", "IndexedQuadSet"):
        per_face = 3 if g == "IndexedTriangleSet" else 4
        return geometry.indexed(points, [int(i) for i in mathx.floats(element.get("index", ""))], per_face, ccw)
    if g in ("TriangleSet", "QuadSet"):
        per_face = 3 if g == "TriangleSet" else 4
        return geometry.indexed(points, list(range(len(points) // 3)), per_face, ccw)
    if g == "ElevationGrid":
        return geometry.elevation_grid(int(_field(element, g, "xDimension")), int(_field(element, g, "zDimension")),
                                       float(_field(element, g, "xSpacing")), float(_field(element, g, "zSpacing")),
                                       _floats(element, g, "height"), ccw)
    return None


class _Loader:
    def __init__(self, path):
        self.path = Path(path)
        root = etree.parse(str(self.path), etree.XMLParser(load_dtd=False, no_network=True, remove_comments=True)).getroot()
        unit, source = _unit(root)
        self.scene = Scene(path=self.path, unit=unit, unit_source=source)
        self.defs = {}
        self.unnamed = 0
        self._scene_element(root, self.path, np.eye(4), depth=0)

    def _scene_element(self, root, path, matrix, depth):
        scene = next((c for c in root.iter() if _tag(c) == "Scene"), None)
        if scene is None:
            raise ValueError(f"{path}: no <Scene> element")
        ctx = dict(object=None, mover=None, rendered=True, collidable=True, file=path, root=depth == 0)
        for child in scene:
            self._node(child, matrix, ctx, depth, top_level=True)

    def _resolve(self, element):
        use = element.get("USE")
        if use:
            if use not in self.defs:
                self.scene.notes.append(f"USE='{use}' before its DEF; ignored")
                return None
            return self.defs[use]
        if element.get("DEF"):
            self.defs[element.get("DEF")] = element
        return element

    def _node(self, element, matrix, ctx, depth, top_level=False):
        if not isinstance(element.tag, str):
            return
        node = self._resolve(element)
        if node is None:
            return
        t = _tag(node)
        name = element.get("DEF") or element.get("USE")
        if t in TRANSFORMING:
            local = mathx.transform_matrix(_floats(node, t, "translation"), _floats(node, t, "rotation"),
                                           _floats(node, t, "scale"), _floats(node, t, "scaleOrientation"),
                                           _floats(node, t, "center"))
            if top_level and ctx["root"] and t == "Transform":
                self.scene.root_rotations.append((name, tuple(_floats(node, t, "rotation"))))
            child_ctx = dict(ctx)
            if name:
                child_ctx.update(object=name, mover=name, mover_parent=matrix,
                                 mover_translation=np.array(_floats(node, t, "translation")))
            self._children(node, matrix @ local, child_ctx, depth)
        elif t in GROUPING:
            child_ctx = dict(ctx)
            if name:
                child_ctx["object"] = name
            if (node.get("visible") or "true").lower() == "false":
                child_ctx["rendered"] = False
            if t == "Collision":
                enabled = _bool(node, t, "enabled")
                proxy = [c for c in node if isinstance(c.tag, str) and c.get("containerField") == "proxy"]
                child_ctx["collidable"] = ctx["collidable"] and (enabled and not proxy)
                for p in proxy:
                    self._node(p, matrix, dict(child_ctx, rendered=False, collidable=enabled,
                                               object=(name or "Collision") + " proxy"), depth)
            if t == "Switch":
                choice = int(_field(node, t, "whichChoice"))
                kids = [c for c in node if isinstance(c.tag, str) and c.get("containerField", "children") == "children"]
                for i, c in enumerate(kids):
                    self._node(c, matrix, dict(child_ctx, rendered=child_ctx["rendered"] and i == choice,
                                               collidable=child_ctx["collidable"] and i == choice), depth)
                return
            if t == "LOD":
                kids = [c for c in node if isinstance(c.tag, str)]
                if kids:
                    self.scene.notes.append(f"LOD {name or ''}: using its first (most detailed) level")
                    self._node(kids[0], matrix, child_ctx, depth)
                return
            if t == "Billboard":
                self.scene.notes.append(f"Billboard {name or ''}: orientation depends on the viewer; drawn unrotated")
            self._children(node, matrix, child_ctx, depth)
        elif t == "Shape":
            self._shape(node, matrix, dict(ctx, object=ctx["object"] or name))
        elif t in VIEWPOINTS and ctx["root"]:
            self._viewpoint(node, t, name, matrix)
        elif t == "NavigationInfo" and ctx["root"] and node.get("containerField", "children") == "children":
            self.scene.navigation_infos.append(_navigation_info(node, name or f"NavigationInfo{len(self.scene.navigation_infos)}"))
        elif t == "Background" and self.scene.background_sky is None:
            sky = mathx.floats(node.get("skyColor", "0 0 0"))
            self.scene.background_sky = tuple(sky[:3]) if len(sky) >= 3 else (0.0, 0.0, 0.0)
        elif t == "Fog" and not self.scene.fog_range:
            self.scene.fog_range = float(_field(node, t, "visibilityRange") or 0)
        elif t == "RigidBodyCollection":
            self.scene.physics_gravity.append(_floats(node, t, "gravity"))
        elif t.startswith("Geo"):
            self.scene.geospatial = True
        elif t == "Inline":
            self._inline(node, matrix, ctx, depth)

    def _children(self, node, matrix, ctx, depth):
        for child in node:
            if isinstance(child.tag, str) and child.get("containerField", "children") == "children":
                self._node(child, matrix, ctx, depth)

    def _shape(self, node, matrix, ctx):
        geom = next((c for c in node if isinstance(c.tag, str) and _tag(c) != "Appearance"
                     and not _tag(c).startswith("Metadata")), None)
        geom = self._resolve(geom) if geom is not None else None
        if geom is None:
            return
        g = _tag(geom)
        local = _geometry(geom, g)
        if local is None:
            if g not in ("IndexedLineSet", "LineSet", "PointSet", "Text"):
                self.scene.notes.append(f"{g}: not tessellated; left out of the view")
            return
        color, transparency = None, 0.0
        appearance = next((c for c in node if _tag(c) == "Appearance"), None)
        appearance = self._resolve(appearance) if appearance is not None else None
        if appearance is not None:
            material = next((c for c in appearance if _tag(c) in ("Material", "PhysicalMaterial", "UnlitMaterial")), None)
            material = self._resolve(material) if material is not None else None
            if material is not None:
                mt = _tag(material)
                key = "baseColor" if mt == "PhysicalMaterial" else "emissiveColor" if mt == "UnlitMaterial" else "diffuseColor"
                color = tuple(_floats(material, mt, key)[:3]) or None
                transparency = float(_field(material, mt, "transparency") or 0)
        name = ctx["object"]
        if not name:
            self.unnamed += 1
            name = f"{g}#{self.unnamed}"
        solid_default = default(g, "solid")
        solid = _bool(geom, g, "solid") if solid_default is not None else True
        world = mathx.apply(mathx.uniform_scale(self.scene.unit) @ matrix, local.reshape(-1, 3)).reshape(-1, 3, 3)
        self.scene.shapes.append(ShapeRecord(
            object=name, geometry=g, triangles=world, diffuse_color=color, transparency=transparency, solid=solid,
            rendered=ctx["rendered"], collidable=ctx["collidable"], mover=ctx.get("mover"),
            mover_parent_matrix=ctx.get("mover_parent"), mover_translation=ctx.get("mover_translation")))

    def _viewpoint(self, node, t, name, matrix):
        nav = None
        for c in node:
            if isinstance(c.tag, str) and _tag(c) == "NavigationInfo" and c.get("containerField") == "navigationInfo":
                resolved = self._resolve(c)
                nav = _navigation_info(resolved, c.get("DEF") or c.get("USE") or "navigationInfo")
        fov = _floats(node, t, "fieldOfView")
        self.scene.viewpoints.append(Viewpoint(
            name=name or node.get("description") or f"{t}{len(self.scene.viewpoints)}", kind=t,
            description=node.get("description", ""), position=np.array(_floats(node, t, "position")),
            orientation=tuple(_floats(node, t, "orientation")), field_of_view=fov[0] if t == "Viewpoint" else fov,
            near_distance=float(_field(node, t, "nearDistance")), far_distance=float(_field(node, t, "farDistance")),
            parent_matrix=matrix, navigation_info=nav))

    def _inline(self, node, matrix, ctx, depth):
        for url in _mfstring(node.get("url")):
            if urlparse(url).scheme in ("http", "https") or not url.lower().endswith(".x3d"):
                continue
            target = (ctx["file"].parent / url).resolve()
            if not target.is_file():
                continue
            if depth > 8:
                self.scene.notes.append(f"Inline {url}: nested too deeply; skipped")
                return
            inner = etree.parse(str(target), etree.XMLParser(load_dtd=False, no_network=True, remove_comments=True)).getroot()
            inner_unit, _ = _unit(inner)
            scale = mathx.uniform_scale(inner_unit / self.scene.unit)
            scene = next((c for c in inner.iter() if _tag(c) == "Scene"), None)
            inner_ctx = dict(ctx, file=target, root=False)
            for child in scene:
                self._node(child, matrix @ scale, inner_ctx, depth + 1)
            return
        self.scene.notes.append(f"Inline {node.get('url')}: no local .x3d file found; left out")


def load(path):
    """Parse an X3D XML file into a Scene."""
    return _Loader(path).scene
