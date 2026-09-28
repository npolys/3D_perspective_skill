"""The README's capture example, end to end, in both renderers.

In its own module because Playwright's sync API allows one session per thread, and the
module-scoped sessions in test_live.py are closed when that module finishes.
"""

import json

import pytest

from conftest import ROOM
from perspective_agent import cli

pytestmark = pytest.mark.live


@pytest.mark.parametrize("renderer", ["x_ite", "x3dom"])
def test_capture_with_a_field_change(tmp_path, capsys, renderer):
    # Move the table right of the lamp as seen from Side, capture, and compare with the imagined view.
    pytest.importorskip("playwright")
    cli.main(["capture", str(ROOM), "--renderer", renderer, "--viewpoint", "Side",
              "--set", "Table.translation=-1.5 0.375 -1.75", "--out", str(tmp_path / "side.png")])
    result = json.loads(capsys.readouterr().out)
    assert result["notes"] == [] and result["page_errors"] == []
    assert [o["name"] for o in result["objects"] if o["agrees"] is False] == []
    assert (tmp_path / "side.png").stat().st_size > 10_000
