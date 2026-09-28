"""The skill against real renderers: every viewpoint of the room, in both X_ITE and X3DOM.

For each viewpoint and renderer the test binds the Viewpoint in the live browser and checks that:
- the live camera is where the skill imagines the eye (including WALK settling, which differs by renderer);
- each coloured object lands where the skill imagined it, as found by colour in the capture;
- "put that box to the right of the sphere" moves the box so it appears right of the sphere.

Run with: pytest --live   (needs pip install -e .[live], python -m playwright install chromium, and network).
"""

import pytest

from x3d_perspective import perspective, relations, view, x3d_loader

from conftest import ROOM

pytestmark = pytest.mark.live
VIEWPOINTS = ["Entry", "Side", "Corner", "Overlook"]
TABLE_HOME = "0 0.375 0"


@pytest.fixture(scope="module")
def scene():
    return x3d_loader.load(ROOM)


@pytest.fixture(scope="module", params=["x_ite", "x3dom"])
def session(request):
    pytest.importorskip("playwright")
    pytest.importorskip("PIL")
    from x3d_perspective.live import LiveView
    with LiveView(ROOM, renderer=request.param) as live:
        yield live


def center_u(found):
    return (found["box"][0] + found["box"][2]) / 2


@pytest.mark.parametrize("viewpoint", VIEWPOINTS)
def test_live_view_matches_the_imagined_view(scene, session, viewpoint):
    from x3d_perspective import verify
    result = verify.check_viewpoint(session, scene, viewpoint)
    assert result["problems"] == []
    assert [row["name"] for row in result["objects"]] == ["Table", "Lamp", "Plant"]   # the colored objects


@pytest.mark.parametrize("viewpoint", VIEWPOINTS)
def test_put_that_box_to_the_right_of_the_sphere(scene, session, viewpoint):
    from x3d_perspective import imaging, verify
    session.bind(viewpoint)
    p = perspective.from_viewpoint(scene, viewpoint, renderer=session.renderer)
    box = relations.resolve(scene, p, "that box")["match"]
    sphere = relations.resolve(scene, p, "the sphere")["match"]
    plan = relations.place(scene, p, box, "right of", sphere)
    change = plan["set_field"]
    try:
        session.set_field(change["def"], change["field"], change["value"])
        seen = imaging.object_boxes(session.capture(), verify.object_colors(scene))
    finally:
        session.set_field(change["def"], change["field"], TABLE_HOME)
    assert center_u(seen[box]) > center_u(seen[sphere]), "box is not right of the sphere in the capture"
    moved = relations.with_translation(scene, change["def"], change["value"])
    assert [row for row in verify.compare(view.see(moved, p), seen) if not row["agrees"]] == []
