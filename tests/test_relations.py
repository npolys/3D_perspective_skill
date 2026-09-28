"""Viewer-relative directions, object relations and placement (docs/X3D_MAPPINGS.md §3)."""

import pytest

from x3d_perspective import perspective, relations, x3d_loader

from conftest import ROOM, write_scene

# "Put that box to the right of the sphere", from each viewpoint of the room.
RIGHT_OF_LAMP = {
    "Entry": ([1, 0, 0], "-0.55 0.375 -1"),
    "Side": ([0, 0, -1], "-1.5 0.375 -1.75"),
    "Corner": ([0.8253, 0, 0.5646], "-0.616 0.375 -0.3952"),
    "Overlook": ([1, 0, 0], "-0.55 0.375 -1"),     # pitched down, but "right" stays level
}


@pytest.fixture(scope="module")
def room():
    return x3d_loader.load(ROOM)


@pytest.mark.parametrize("viewpoint", RIGHT_OF_LAMP)
def test_right_depends_on_the_viewpoint(room, viewpoint):
    right = perspective.from_viewpoint(room, viewpoint).directions()["right of"]
    assert right == pytest.approx(RIGHT_OF_LAMP[viewpoint][0], abs=1e-3)


@pytest.mark.parametrize("viewpoint", RIGHT_OF_LAMP)
def test_put_that_box_to_the_right_of_the_sphere(room, viewpoint):
    p = perspective.from_viewpoint(room, viewpoint)
    box = relations.resolve(room, p, "that box")["match"]
    sphere = relations.resolve(room, p, "the sphere")["match"]
    assert (box, sphere) == ("Table", "Lamp")
    plan = relations.place(room, p, box, "right of", sphere)
    assert plan["set_field"] == {"def": "Table", "field": "translation", "value": RIGHT_OF_LAMP[viewpoint][1]}
    assert plan["relation_holds"] and plan["overlaps"] == []
    assert plan["notes"] == ["rests on Floor, as it rested on Floor"]
    after = plan["imagined_after"]
    assert after["Table"]["center_px"][0] > after["Lamp"]["center_px"][0]      # right of it in the image


def test_setting_the_suggested_translation_gives_the_imagined_view(room):
    from x3d_perspective import view
    p = perspective.from_viewpoint(room, "Side")
    plan = relations.place(room, p, "Table", "right of", "Lamp")
    moved = relations.with_translation(room, "Table", plan["set_field"]["value"])
    after = {o["name"]: o for o in view.see(moved, p)["objects"]}
    assert after["Table"]["pixel_box"] == pytest.approx(plan["imagined_after"]["Table"]["pixel_box"], abs=0.1)
    assert relations.with_translation(room, "NoSuchDEF", "0 0 0") is None


def test_relations_are_judged_from_the_viewer(room):
    entry = relations.relations_between(room, perspective.from_viewpoint(room, "Entry"), "Table", "Lamp")
    side = relations.relations_between(room, perspective.from_viewpoint(room, "Side"), "Table", "Lamp")
    assert entry["relations"] == ["right of", "in front of", "below"]
    assert side["relations"] == ["left of", "in front of", "below"]


def test_resolve_skips_floors_and_walls_and_asks_when_ambiguous(tmp_path):
    room = x3d_loader.load(ROOM)
    assert relations.resolve(room, None, "Floor")["match"] == "Floor"
    two = x3d_loader.load(write_scene(tmp_path, '<Viewpoint position="0 1 8"/>'
                                      '<Transform DEF="A" translation="-1 0 0">'
                                      '<Shape><Box size="0.5 0.5 0.5"/></Shape></Transform>'
                                      '<Transform DEF="B" translation="1 0 0">'
                                      '<Shape><Box size="0.5 0.5 0.5"/></Shape></Transform>'))
    answer = relations.resolve(two, perspective.from_viewpoint(two), "that box")
    assert answer["match"] is None and set(answer["candidates"]) == {"A", "B"}


def test_placement_in_a_rotated_scaled_parent(tmp_path):
    scene = x3d_loader.load(write_scene(
        tmp_path, '<Viewpoint position="0 1.6 6"/>'
        '<Transform DEF="Room" rotation="0 1 0 1.5708" scale="2 2 2">'
        '<Transform DEF="Crate" translation="0 0.25 0"><Shape><Box size="0.5 0.5 0.5"/></Shape></Transform></Transform>'
        '<Transform DEF="Ball" translation="-2 0.5 0"><Shape><Sphere radius="0.5"/></Shape></Transform>'))
    p = perspective.from_viewpoint(scene)
    plan = relations.place(scene, p, "Crate", "right of", "Ball", gap=0)
    # World: ball right edge x = -1.5, crate half-width 0.5 (scaled 2x), so crate center x = -1.0.
    assert plan["new_center_m"] == pytest.approx([-1.0, 0.5, 0.0], abs=1e-3)
    moved = relations.moved_scene(scene, "Crate", [-1.0, 0, 0])
    assert moved.objects()["Crate"][0].triangles.reshape(-1, 3).mean(axis=0)[0] == pytest.approx(-1.0)
    # The new translation is in the parent frame (rotated +90 deg about Y, scaled 2x): world -X is local -Z / 2.
    x, y, z = map(float, plan["set_field"]["value"].split())
    assert (x, y, z) == pytest.approx((0, 0.25, -0.5), abs=1e-3)
