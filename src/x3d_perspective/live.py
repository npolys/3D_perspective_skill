"""Drive the live X3D view in X_ITE or X3DOM: bind viewpoints, change fields, read the camera, capture.

Runs a headless browser through Playwright (pip install -e .[live], then
python -m playwright install chromium). The scene's directory is served on a loopback port so
relative URLs resolve as they do on a web page; the page itself is served from memory, so nothing
is written next to the scene.

    with LiveView("room.x3d", renderer="x3dom") as live:
        live.bind("Side")
        live.set_field("Table", "translation", "-1.5 0.375 -1.75")
        png = live.capture()
"""

import functools
import http.server
import threading
from pathlib import Path

import numpy as np
from lxml import etree

from . import mathx
from .x3d_loader import _defaults, _tag, parse_xml

RENDERERS = ("x_ite", "x3dom")
# Pinned so captures are repeatable; the versions the live tests were verified with.
X_ITE_VERSION = "16.4.1"
X3DOM_VERSION = "1.8.3"
X_ITE_SCRIPT = "https://cdn.jsdelivr.net/npm/x_ite@{version}/dist/x_ite.min.js"
X3DOM_BASE = "https://www.x3dom.org/download/{version}/"
PAGE = "__perspective_live__.html"
# Software GL, so captures work without a GPU. Same flags as x3d_mcp's renderer and the x3dom-spikes;
# X3DOM also needs Chrome's full headless mode (channel "chromium"), not the headless shell.
# Default launch args intentionally do NOT include '--no-sandbox'. This option may be supplied
# when running in an environment that requires it (for example some CI systems). See README for security notes.
LAUNCH_ARGS_BASE = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                    "--ignore-gpu-blocklist", "--hide-scrollbars"]
SETTLE_MS = 1500            # after load or a field change: a few frames, and WALK settling
BIND_MS = 2500              # after a bind: the default 1 s transition, then settling
VECTOR_TYPES = {"SFVec2f", "SFVec3f", "SFVec3d", "SFColor", "SFColorRGBA", "SFRotation", "SFVec4f"}


def _x_ite_page(scene_name, width, height, version):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="{X_ITE_SCRIPT.format(version=version)}"></script>
<style>html,body{{margin:0;overflow:hidden;background:#000}}x3d-canvas{{width:{width}px;height:{height}px;display:block}}</style>
</head><body><x3d-canvas src="{scene_name}" splashScreen="false" notifications="false" contextMenu="false"></x3d-canvas>
</body></html>"""


def _x3dom_page(scene_path, width, height, version):
    """Embed the scene's children in an X3DOM page (the approach of x3d_mcp's x3dom_page)."""
    root = parse_xml(scene_path)
    scene = next(c for c in root.iter() if _tag(c) == "Scene")
    body = "".join(etree.tostring(c, method="html", encoding="unicode") for c in scene if isinstance(c.tag, str))
    base = X3DOM_BASE.format(version=version)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{base}x3dom.css"><script src="{base}x3dom-full.js"></script>
<style>html,body{{margin:0;overflow:hidden;background:#000}}</style>
</head><body><x3d id="x3d" width="{width}px" height="{height}px" showStat="false" showLog="false" disableDoubleClick="true">
<scene>{body}</scene></x3d></body></html>"""


class _Handler(http.server.SimpleHTTPRequestHandler):
    page = b""

    def do_GET(self):
        if self.path.split("?")[0].lstrip("/") == PAGE:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(self.page)))
            self.end_headers()
            self.wfile.write(self.page)
            return
        super().do_GET()

    def log_message(self, *args):
        pass


class LiveView:
    def __init__(self, scene_path, renderer="x_ite", size=(1280, 720), x_ite_version=X_ITE_VERSION,
                 x3dom_version=X3DOM_VERSION, allow_no_sandbox=False, launch_args=None):
        """LiveView(scene_path, renderer, size, allow_no_sandbox=False, launch_args=None)

        allow_no_sandbox: when True, append '--no-sandbox' to the Chromium launch args. Defaults to False
        to avoid running Chromium without its sandbox. For environments that require it (some CI), set True.

        launch_args: optional list overriding the default launch arguments entirely.
        """
        if renderer not in RENDERERS:
            raise ValueError(f"renderer must be one of {RENDERERS}")
        self.scene_path = Path(scene_path).resolve()
        self.renderer = renderer
        self.size = size
        self.versions = {"x_ite": x_ite_version, "x3dom": x3dom_version}
        self.errors = []
        root = parse_xml(self.scene_path)
        self._types = {e.get("DEF"): _tag(e) for e in root.iter() if isinstance(e.tag, str) and e.get("DEF")}
        # Determine launch args: explicit override, otherwise use base plus optional --no-sandbox.
        if launch_args is not None:
            self.launch_args = list(launch_args)
        else:
            self.launch_args = list(LAUNCH_ARGS_BASE)
            if allow_no_sandbox:
                self.launch_args.append("--no-sandbox")

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()

    def open(self):
        from playwright.sync_api import sync_playwright
        width, height = self.size
        html = (_x_ite_page(self.scene_path.name, width, height, self.versions["x_ite"]) if self.renderer == "x_ite"
                else _x3dom_page(self.scene_path, width, height, self.versions["x3dom"]))
        handler = functools.partial(type("Handler", (_Handler,), {"page": html.encode("utf-8")}),
                                    directory=str(self.scene_path.parent))
        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()
        self._playwright = sync_playwright().start()
        # Use the configured launch args (defaults avoid --no-sandbox).
        self._browser = self._playwright.chromium.launch(channel="chromium", args=self.launch_args)
        self.page = self._browser.new_page(viewport={"width": width, "height": height})
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.goto(f"http://127.0.0.1:{self._httpd.server_address[1]}/{PAGE}", wait_until="load")
        self._wait_ready()
        return self

    def close(self):
        if getattr(self, "_browser", None):
            self._browser.close()
        if getattr(self, "_playwright", None):
            self._playwright.stop()
        if getattr(self, "_httpd", None):
            self._httpd.shutdown()

    def _wait_ready(self):
        if self.renderer == "x_ite":
            self.page.wait_for_function("""() => { const c = document.querySelector("x3d-canvas");
                return c && c.browser && c.browser.currentScene && c.browser.currentScene.rootNodes.length > 0; }""",
                                        timeout=30000)
            # A world-sized ProximitySensor reports the viewer's position and orientation (portable X3D).
            self.page.evaluate("""() => { const b = document.querySelector("x3d-canvas").browser, s = b.currentScene;
                const ps = s.createNode("ProximitySensor"); ps.size = new X3D.SFVec3f(1e6, 1e6, 1e6);
                s.rootNodes.push(ps); window.__viewer = ps; }""")
        else:
            self.page.wait_for_function("""() => { const x = document.getElementById("x3d");
                return x && x.runtime && x.runtime.canvas && x.runtime.canvas.doc; }""", timeout=30000)
        self.page.wait_for_timeout(SETTLE_MS)

    def bind(self, viewpoint):
        """Bind a Viewpoint by DEF name, as the user choosing it from the browser's viewpoint list."""
        if self.renderer == "x_ite":
            self.page.evaluate("n => document.querySelector('x3d-canvas').browser.changeViewpoint(n)", viewpoint)
        else:
            self.page.evaluate("n => document.querySelector(`[DEF='${n}']`).setAttribute('set_bind', 'true')", viewpoint)
        self.page.wait_for_timeout(BIND_MS)

    def set_field(self, def_name, field, value):
        """Set a field on a DEF'd node in the running scene, from its X3D string value."""
        if self.renderer == "x3dom":
            self.page.evaluate("([d, f, v]) => document.querySelector(`[DEF='${d}']`).setAttribute(f, v)",
                               [def_name, field, value])
        else:
            node_type = self._types.get(def_name)
            field_type = _defaults().get(node_type, {}).get("fields", {}).get(field, {}).get("type", "SFString")
            numeric = field_type in VECTOR_TYPES or field_type in ("SFFloat", "SFDouble", "SFInt32")
            numbers = mathx.floats(value) if numeric else []
            self.page.evaluate("""([d, f, t, v, nums]) => {
                const node = document.querySelector("x3d-canvas").browser.currentScene.getNamedNode(d);
                if (X3D[t] && nums.length > 1) node[f] = new X3D[t](...nums);
                else if (nums.length === 1) node[f] = nums[0];
                else if (t === "SFBool") node[f] = v.trim().toLowerCase() === "true";
                else node[f] = v; }""", [def_name, field, field_type, value, numbers])
        self.page.wait_for_timeout(SETTLE_MS)

    def camera(self):
        """The live camera in world coordinates: position and right/up/forward axes."""
        if self.renderer == "x3dom":
            m = self.page.evaluate("""() => { const m = document.getElementById("x3d").runtime.viewMatrix().inverse();
                return [[m._00, m._01, m._02, m._03], [m._10, m._11, m._12, m._13], [m._20, m._21, m._22, m._23]]; }""")
            m = np.array(m)
            rotation, position = m[:, :3], m[:, 3]
        else:
            values = self.page.evaluate("""() => {
                const p = window.__viewer.position_changed, o = window.__viewer.orientation_changed;
                return [p.x, p.y, p.z, o.x, o.y, o.z, o.angle]; }""")
            position, rotation = np.array(values[:3]), mathx.rotation(values[3:])
        rotation = mathx.frame_rotation(np.vstack([np.hstack([rotation, [[0], [0], [0]]]), [0, 0, 0, 1]]))
        return {"position": position, "right": rotation[:, 0], "up": rotation[:, 1], "forward": -rotation[:, 2]}

    def project(self, points):
        """The renderer's own world-to-pixel projection (X3DOM calcCanvasPos); None for X_ITE."""
        if self.renderer != "x3dom":
            return None
        return self.page.evaluate("""pts => { const r = document.getElementById("x3d").runtime;
            return pts.map(p => r.calcCanvasPos(p[0], p[1], p[2])); }""", [list(map(float, p)) for p in points])

    def capture(self, path=None, include_id_map=False):
        """Capture the visible canvas. If include_id_map is True, also produce an
        object-id encoded capture where each DEF'd node is temporarily recolored to a
        unique flat RGB so imaging can deterministically locate objects.

        Returns:
            If include_id_map is False: PNG bytes (same as before).
            If include_id_map is True: dict {"png": <bytes>, "id_png": <bytes>, "id_colors": {name: [r,g,b]}}
        """
        # Regular color capture
        png = self.page.locator("canvas").first.screenshot()
        if not include_id_map:
            if path:
                Path(path).write_bytes(png)
            return png

        # Build an id-color mapping for each DEF'd node available in the scene
        names = self.page.evaluate("() => Array.from(document.querySelectorAll('[DEF]')).map(n => n.getAttribute('DEF'))")
        # deterministic mapping: use a simple hashed palette in 24-bit RGB (avoid black and near-black)
        def _name_to_rgb(name):
            h = 2166136261
            for ch in name:
                h = (h ^ ord(ch)) * 16777619 & 0xFFFFFFFF
            # produce saturated color away from black/white
            r = (h >> 16) & 0xFF
            g = (h >> 8) & 0xFF
            b = h & 0xFF
            # nudge away from extremes
            r = (r + 64) % 256
            g = (g + 128) % 256
            b = (b + 192) % 256
            # avoid very dark colors (reserve near-black for background)
            if r < 16 and g < 16 and b < 16:
                r = (r + 32) % 256
            return [r, g, b]

        id_colors = {n: _name_to_rgb(n) for n in names}

        # Evaluate a page script to temporarily recolor DEF'd nodes to their id color.
        # This is best-effort: record prior values and restore them afterwards.
        recolor_script = """
        (map) => {
            function setColorOnNode(node, rgb) {
                // try X3DOM style: find Appearance/Material children
                try {
                    const mats = node.getElementsByTagName('Material');
                    if (mats && mats.length) {
                        Array.from(mats).forEach(m => { m.setAttribute('diffuseColor', rgb); m.setAttribute('emissiveColor', rgb); });
                        return true;
                    }
                } catch (e) {}
                // try x_ite: set browser node material if present
                try {
                    if (node.setAttribute) { node.setAttribute('diffuseColor', rgb); return true; }
                } catch (e) {}
                return false;
            }
            const names = Object.keys(map);
            const saved = [];
            for (const n of names) {
                const node = document.querySelector("[DEF='" + n + "']");
                if (!node) continue;
                // save existing material attributes where possible
                const mats = node.getElementsByTagName ? node.getElementsByTagName('Material') : [];
                const prev = [];
                for (const m of mats) prev.push(m.getAttribute('diffuseColor'));
                saved.push({name: n, node: node, mats: mats, prev: prev});
                const rgb = map[n].join(' ');
                setColorOnNode(node, rgb);
            }
            // small pause to let the renderer update
            return saved;
        }
        """
        saved = self.page.evaluate(recolor_script, id_colors)
        # allow a couple frames for the recolor to become visible
        self.page.wait_for_timeout(80)
        id_png = self.page.locator("canvas").first.screenshot()

        # restore previous material attributes
        restore_script = """
        (saved) => {
            for (const s of saved) {
                try {
                    if (!s || !s.node) continue;
                    if (s.mats && s.mats.length) {
                        for (let i = 0; i < s.mats.length; ++i) {
                            const m = s.mats[i];
                            const prev = s.prev[i];
                            if (prev === null || prev === undefined) m.removeAttribute('diffuseColor');
                            else m.setAttribute('diffuseColor', prev);
                        }
                    }
                    // fallback: remove any temporary attributes
                    if (s.node && s.node.removeAttribute) {
                        try { s.node.removeAttribute('diffuseColor'); } catch (e) {}
                        try { s.node.removeAttribute('emissiveColor'); } catch (e) {}
                    }
                } catch (e) {}
            }
            return true;
        }
        """
        try:
            self.page.evaluate(restore_script, saved)
        except Exception:
            # best-effort restore; ignore failures but record the error
            self.errors.append('Failed to restore recolor state')

        # write files if requested (write both color and id map)
        if path:
            p = Path(path)
            p.write_bytes(png)
            idpath = p.with_name(p.stem + "_idmap" + p.suffix)
            idpath.write_bytes(id_png)

        return {"png": png, "id_png": id_png, "id_colors": id_colors}
