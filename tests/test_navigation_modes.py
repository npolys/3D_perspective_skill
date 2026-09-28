import numpy as np

from x3d_perspective import geometry, x3d_loader, perspective


def _make_scene():
    scene = x3d_loader.Scene(path='scene.x3d', unit=1.0, unit_source='default (meters)')
    vp = x3d_loader.Viewpoint(
        name='Main', kind='Viewpoint', description='Main',
        position=np.array([0.0, 1.6, 5.0]), orientation=(0.0, 0.0, 0.0, 0.0),
        field_of_view=0.7854, near_distance=0.1, far_distance=100.0,
        parent_matrix=np.eye(4),
        navigation_info=x3d_loader.NavigationInfo(
            name='nav', type=['EXAMINE'], avatar_size=[0.25, 1.6, 0.75], speed=1.0,
            visibility_limit=100.0, headlight=True, transition_time=0.0,
        ),
    )
    scene.viewpoints = [vp]
    scene.navigation_infos = [vp.navigation_info]
    scene.shapes = [
        x3d_loader.ShapeRecord(
            object='Floor', geometry='Box', triangles=geometry.box((10.0, 0.2, 10.0)),
            diffuse_color=(0.8, 0.8, 0.8), transparency=0.0, solid=True, rendered=True,
            collidable=True, mover=None, mover_parent_matrix=None, mover_translation=None,
        )
    ]
    return scene


def test_non_walk_navigation_keeps_authored_eye():
    scene = _make_scene()
    p = perspective.from_viewpoint(scene, 'Main')
    assert p.navigation_mode == 'EXAMINE'
    assert p.walk is False
    assert np.allclose(p.eye, p.authored_eye)
    assert p.target is not None
    assert p.orbit_radius is not None
    assert any('EXAMINE' in note for note in p.notes)


def test_fly_navigation_keeps_free_flight_and_persistent_up():
    scene = _make_scene()
    scene.viewpoints[0].navigation_info.type = ['FLY']
    p = perspective.from_viewpoint(scene, 'Main')
    assert p.navigation_mode == 'FLY'
    assert p.walk is False
    assert np.allclose(p.eye, p.authored_eye)
    assert p.target is None
    assert p.orbit_radius is None
    assert any('FLY' in note for note in p.notes)


def test_walk_navigation_still_sets_support():
    scene = _make_scene()
    scene.viewpoints[0].navigation_info.type = ['WALK']
    p = perspective.from_viewpoint(scene, 'Main')
    assert p.navigation_mode == 'WALK'
    assert p.walk is True
    assert p.eye is not None
    assert p.support == 'Floor'
