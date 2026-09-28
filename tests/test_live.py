"""The skill against real renderers: every viewpoint of the room, in both X_ITE and X3DOM.

For each viewpoint and renderer the test binds the Viewpoint in the live browser and checks that:
- the live camera is where the skill imagines the eye (including WALK settling, which differs by renderer);
- each coloured object lands where the skill imagined it, as found by colour in the capture;
- "put that box to the right of the sphere" moves the box so it appears right of the sphere.

Run with: pytest --live   (needs pip install -e .[live], python -m playwright install chromium, and network).
"""

import numpy as np
import pytest

from conftest import ROOM
from perspective_agent import perspective, relations, view, x3d_loader

pytestmark = pytest.mark.live
VIEWPOINTS = ["Entry", "Side", "Corner", "Overlook"]
TOLERANCE_PX = 3            # shading at silhouette edges; the darkest faces read as black
TABLE_HOME = "0 0.375 0"


@pytest.fixture(scope="module")
def scene():
    return x3d_loader.load(ROOM)


@pytest.fixture(scope="module", params=["x_ite", "x3dom"])
def session(request):
    pytest.importorskip("playwright")
    pytest.importorskip("PIL")
    from perspective_agent.live import LiveView
    with LiveView(ROOM, renderer=request.param) as live:
        yield live


def colors(scene):
    return {n: next((s.diffuse_color for s in shapes if s.diffuse_color), None) for n, shapes in scene.objects().items()}


def check_boxes(imagined, seen, tolerance=TOLERANCE_PX):
    """Fully visible objects must match; partly hidden ones must lie within their imagined outline."""
    from perspective_agent import imaging
    problems = []
    for name, found in seen.items():
        entry = imagined.get(name, {})
        if found is None or entry.get("status") != "VISIBLE":
            continue
        if entry.get("visible_fraction") == 1.0:
            if not imaging.agrees(entry["pixel_box"], found, tolerance):
                problems.append(f"{name}: seen {found}, imagined {entry['pixel_box']}")
        elif not imaging.within(entry["pixel_box"], found, tolerance):
            problems.append(f"{name}: seen {found} outside imagined {entry['pixel_box']}")
    return problems


def center_u(found):
    return (found["box"][0] + found["box"][2]) / 2


@pytest.mark.parametrize("viewpoint", VIEWPOINTS)
def test_live_view_matches_the_imagined_view(scene, session, viewpoint):
    from perspective_agent import imaging
    session.bind(viewpoint)
    p = perspective.from_viewpoint(scene, viewpoint, renderer=session.renderer)
    camera = session.camera()
    assert camera["position"] == pytest.approx(p.eye, abs=0.01), "live camera is not where the skill puts the eye"
    assert camera["forward"] == pytest.approx(p.forward, abs=0.01)
    png = session.capture()
    imagined = {o["name"]: o for o in view.see(scene, p)["objects"]}
    assert check_boxes(imagined, imaging.object_boxes(png, colors(scene))) == []
    assert session.errors == []


@pytest.mark.parametrize("viewpoint", VIEWPOINTS)
def test_put_that_box_to_the_right_of_the_sphere(scene, session, viewpoint):
    from perspective_agent import imaging
    session.bind(viewpoint)
    p = perspective.from_viewpoint(scene, viewpoint, renderer=session.renderer)
    box = relations.resolve(scene, p, "that box")["match"]
    sphere = relations.resolve(scene, p, "the sphere")["match"]
    plan = relations.place(scene, p, box, "right of", sphere)
    try:
        session.set_field(plan["set_field"]["def"], "translation", plan["set_field"]["value"])
        seen = imaging.object_boxes(session.capture(), colors(scene))
    finally:
        session.set_field(plan["set_field"]["def"], "translation", TABLE_HOME)
    assert center_u(seen[box]) > center_u(seen[sphere]), "box is not right of the sphere in the capture"
    moved = relations.moved_scene(scene, box, np.array(plan["new_center_m"]) - _center(scene, box))
    assert check_boxes({o["name"]: o for o in view.see(moved, p)["objects"]}, seen) == []


def _center(scene, name):
    points = np.concatenate([s.triangles for s in scene.objects()[name]]).reshape(-1, 3)
    return (points.min(axis=0) + points.max(axis=0)) / 2
