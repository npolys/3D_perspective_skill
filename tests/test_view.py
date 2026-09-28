"""The imagined 2D view (docs/X3D_MAPPINGS.md §1, §2, §7).

Expected pixels were checked against X_ITE and X3DOM captures at 1280x720 (tests/test_live.py).
"""

import json

import pytest

from conftest import ROOM, write_scene
from perspective_agent import cli, perspective, view, x3d_loader


@pytest.fixture(scope="module")
def room():
    return x3d_loader.load(ROOM)


def objects(scene, viewpoint, renderer="spec"):
    return {o["name"]: o for o in view.see(scene, perspective.from_viewpoint(scene, viewpoint, renderer))["objects"]}


def test_hd_focal_length_and_field_of_view(room):
    seen = view.see(room, perspective.from_viewpoint(room, "Entry"))
    assert seen["size"] == [1280, 720]
    assert seen["focal_px"] == pytest.approx(869.1, abs=0.1)
    assert seen["horizontal_fov_deg"] == pytest.approx(72.7, abs=0.1)


def test_entry_view_matches_the_captures(room):
    seen = objects(room, "Entry")
    assert seen["Table"]["pixel_box"] == pytest.approx([495.1, 527.9, 784.9, 720.0], abs=0.2)
    assert seen["Table"]["cut_off"] == ["bottom"]
    assert seen["Lamp"]["center_px"] == pytest.approx([379.3, 429.5], abs=0.2)
    assert seen["BackWall"]["pixel_box"] == pytest.approx([264.8, 184.9, 1015.2, 560.1], abs=0.2)
    assert seen["Plant"]["pixel_box"] == pytest.approx([889.7, 471.0, 971.0, 683.4], abs=0.2)
    assert all(seen[n]["status"] == "VISIBLE" for n in ("Table", "Lamp", "Plant", "BackWall"))


def test_default_box_at_the_default_camera(tmp_path):
    scene = x3d_loader.load(write_scene(tmp_path, "<Shape><Box/></Shape>"))
    box = view.see(scene, perspective.from_viewpoint(scene))["objects"][0]
    assert box["pixel_box"] == pytest.approx([543.4, 263.4, 736.6, 456.6], abs=0.2)   # front face 9 m away


def test_frame_clipping_follows_the_outline_not_the_box(room):
    # From Side the plant is cut by the bottom edge; its in-frame part starts at u 224, as captured.
    plant = objects(room, "Side")["Plant"]
    assert plant["pixel_box"][0] == pytest.approx(224.0, abs=0.5) and plant["cut_off"] == ["bottom"]


def test_occlusion_names_the_occluder(room):
    plant = objects(room, "Corner")["Plant"]
    assert plant["status"] == "VISIBLE" and plant["visible_fraction"] < 1 and plant["occluded_by"] == ["Table"]


def test_walk_eye_depends_on_the_renderer(room):
    # X_ITE applies WALK gravity on bind; X3DOM keeps the authored eye until the user moves.
    assert perspective.from_viewpoint(room, "Overlook", "x_ite").eye == pytest.approx([0, 1.6, 3.5])
    assert perspective.from_viewpoint(room, "Overlook", "x3dom").eye == pytest.approx([0, 2.8, 3.5])
    assert objects(room, "Overlook", "x_ite")["Table"]["pixel_box"] != objects(room, "Overlook", "x3dom")["Table"]["pixel_box"]


def test_viewer_with_no_support_falls(tmp_path):
    scene = x3d_loader.load(write_scene(tmp_path, '<NavigationInfo type=\'"WALK" "ANY"\'/><Viewpoint DEF="Edge" position="0 1.6 4"/>'
                                        '<Transform translation="0 -0.05 0"><Shape><Box size="6 0.1 6"/></Shape></Transform>'))
    falling = view.see(scene, perspective.from_viewpoint(scene, "Edge", "x_ite"))
    assert falling["background_only"] and falling["reason"].startswith("VIEWER_FALLS")
    assert not view.see(scene, perspective.from_viewpoint(scene, "Edge", "x3dom"))["background_only"]


def test_hidden_and_behind(tmp_path):
    scene = x3d_loader.load(write_scene(
        tmp_path, '<Viewpoint position="0 0 10"/>'
        '<Switch DEF="Hidden"><Shape><Box/></Shape></Switch>'
        '<Transform DEF="Behind" translation="0 0 20"><Shape><Box/></Shape></Transform>'
        '<Transform DEF="Right" translation="30 0 0"><Shape><Box/></Shape></Transform>'))
    seen = objects(scene, None)
    assert seen["Hidden"]["status"] == "NOT_RENDERED"
    assert seen["Behind"]["status"] == "OUT_OF_FRUSTUM" and seen["Behind"]["where"] == "behind the viewer"
    assert seen["Right"]["status"] == "OUT_OF_FRUSTUM" and seen["Right"]["where"] == "right of the frame"


def test_cli_see(capsys):
    cli.main(["see", str(ROOM), "--viewpoint", "Side"])
    result = json.loads(capsys.readouterr().out)
    assert result["perspective"]["viewpoint"] == "Side"
    assert {o["name"] for o in result["objects"]} == {"Floor", "BackWall", "Table", "Lamp", "Plant"}
