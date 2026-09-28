"""Frame: up, gravity, units, meter scale and the viewer's body (docs/X3D_MAPPINGS.md §1, §4, §6)."""

import numpy as np
import pytest

from conftest import ROOM, write_scene
from perspective_agent import frames, perspective, x3d_loader

FLOOR = '<Transform DEF="Floor" translation="0 -0.05 0"><Shape><Box size="10 0.1 10"/></Shape></Transform>'


def test_room_frame():
    report = frames.frame(x3d_loader.load(ROOM))
    assert report["units"] == {"meters_per_unit": 1.0, "source": "default (meters)"}
    assert report["up"] == [0.0, 1.0, 0.0] and report["gravity"] == [0.0, -1.0, 0.0]
    assert report["navigation"]["type"] == ["WALK", "ANY"] and report["navigation"]["walk_gravity"]
    assert report["navigation"]["avatarSize"] == [0.25, 1.6, 0.75]
    assert [v["name"] for v in report["viewpoints"]] == ["Entry", "Side", "Corner", "Overlook"]
    structural = {o["name"] for o in report["objects"] if o["structural"]}
    assert structural == {"Floor", "BackWall"}
    assert report["warnings"] == []


def test_viewpoint_under_scale_shrinks_the_body_and_near_plane(tmp_path):
    scene = x3d_loader.load(write_scene(tmp_path, '<NavigationInfo type=\'"WALK" "ANY"\'/>'
                                        '<Transform DEF="Miniature" scale="0.1 0.1 0.1"><Viewpoint DEF="Mouse" position="0 16 30"/></Transform>'
                                        + FLOOR))
    p = perspective.from_viewpoint(scene, "Mouse")
    assert (p.collision_radius, p.eye_height, p.step_height) == pytest.approx((0.025, 0.16, 0.075))
    assert p.near == pytest.approx(0.0125)
    assert p.authored_eye == pytest.approx([0, 1.6, 3])
    assert p.eye == pytest.approx([0, 0.16, 3])          # WALK settles the miniature eye 0.16 m above the floor


def test_centimeter_unit_statement_gives_meters(tmp_path):
    scene = x3d_loader.load(write_scene(
        tmp_path,
        '<NavigationInfo type=\'"WALK" "ANY"\' avatarSize="25 160 75"/><Viewpoint DEF="Door" position="0 160 200"/>'
        '<Transform translation="0 -5 0"><Shape><Box size="600 10 600"/></Shape></Transform>',
        head='<unit category="length" name="centimeters" conversionFactor="0.01"/>'))
    report = frames.frame(scene)
    assert report["units"]["meters_per_unit"] == 0.01
    assert report["extent_m"]["size"] == pytest.approx([6, 0.1, 6])
    p = perspective.from_viewpoint(scene, "Door")
    assert p.eye == pytest.approx([0, 1.6, 2]) and p.collision_radius == pytest.approx(0.25)


def test_z_up_content_rotated_to_y_up_is_reported(tmp_path):
    scene = x3d_loader.load(write_scene(tmp_path, '<Viewpoint position="0 1.6 5"/>'
                                        '<Transform DEF="ZupToYup" rotation="1 0 0 -1.5708"><Shape><Box size="6 6 0.1"/></Shape></Transform>'))
    report = frames.frame(scene)
    assert any("Z-up" in e for e in report["up_evidence"])
    assert report["extent_m"]["size"][1] == pytest.approx(0.1, abs=1e-3)     # the slab is now a floor


def test_z_up_content_without_rotation_is_warned(tmp_path):
    scene = x3d_loader.load(write_scene(tmp_path, '<Viewpoint position="0 1.6 5"/><Shape><Box size="6 6 0.1"/></Shape>'))
    assert any("Z-up" in w for w in frames.frame(scene)["warnings"])


def test_no_viewpoint_uses_the_spec_default_camera(tmp_path):
    p = perspective.from_viewpoint(x3d_loader.load(write_scene(tmp_path, "<Shape><Box/></Shape>")))
    assert p.eye == pytest.approx([0, 0, 10]) and p.forward == pytest.approx([0, 0, -1])
    assert p.up == pytest.approx([0, 1, 0]) and p.field_of_view == pytest.approx(0.7854)
    assert not p.walk                                    # default type "EXAMINE" "ANY": no gravity


def test_right_handed_y_up_default_axes(tmp_path):
    p = perspective.from_viewpoint(x3d_loader.load(write_scene(tmp_path, "<Shape><Box/></Shape>")))
    assert np.cross(p.right, p.camera_up) == pytest.approx(-p.forward)   # right x up = toward the viewer (+Z)
    assert p.right == pytest.approx([1, 0, 0])
