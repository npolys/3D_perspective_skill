"""The capture and verify commands, end to end, in both renderers.

In their own module because Playwright's sync API allows one session per thread, and the
module-scoped sessions in test_live.py are closed when that module finishes.
"""

import json

import pytest

from x3d_perspective import cli

from conftest import ROOM, write_scene

pytestmark = pytest.mark.live


@pytest.fixture(autouse=True)
def needs_live_extra():
    pytest.importorskip("playwright")
    pytest.importorskip("PIL")


@pytest.mark.parametrize("renderer", ["x_ite", "x3dom"])
def test_capture_with_a_field_change(tmp_path, capsys, renderer):
    # The README's example: move the table right of the lamp as seen from Side, capture, compare.
    cli.main(["capture", str(ROOM), "--renderer", renderer, "--viewpoint", "Side",
              "--set", "Table.translation=-1.5 0.375 -1.75", "--out", str(tmp_path / "side.png")])
    result = json.loads(capsys.readouterr().out)
    assert result["notes"] == [] and result["page_errors"] == []
    assert [o["name"] for o in result["objects"] if not o["agrees"]] == []
    assert (tmp_path / "side.png").stat().st_size > 10_000


def test_verify_passes_on_the_room(tmp_path, capsys):
    cli.main(["verify", str(ROOM), "--out-dir", str(tmp_path)])        # exit status 0: no SystemExit
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] and len(report["results"]) == 8                # 4 viewpoints x 2 renderers
    assert len(list(tmp_path.glob("*.png"))) == 8


def test_verify_fails_when_the_viewer_falls(tmp_path, capsys):
    scene = write_scene(tmp_path, '<NavigationInfo type=\'"WALK" "ANY"\'/><Viewpoint DEF="Edge" position="0 1.6 4"/>'
                                  '<Transform translation="0 -0.05 0"><Shape><Box size="6 0.1 6"/></Shape></Transform>')
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["verify", str(scene), "--renderer", "x_ite"])
    assert exit_info.value.code == 1
    report = json.loads(capsys.readouterr().out)
    assert "viewer falls" in report["results"][0]["problems"][0]
