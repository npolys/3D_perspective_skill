from pathlib import Path

import pytest

ROOM = Path(__file__).resolve().parent.parent / "examples" / "room_inspection" / "room.x3d"


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true",
                     help="also run tests that drive X_ITE and X3DOM in a headless browser (needs network)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="drives a headless browser; run with --live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


def write_scene(tmp_path, body, head="", name="scene.x3d"):
    """Write a minimal X3D 4.1 scene and return its path."""
    path = tmp_path / name
    path.write_text(f'<X3D profile="Immersive" version="4.1"><head>{head}</head><Scene>{body}</Scene></X3D>',
                    encoding="utf-8")
    return path
