from x3d_perspective_architect import PerspectiveArchitect
def test_human():
 assert PerspectiveArchitect().generate({"observer_type":"HumanPerspective"}).navigation_model["mode"]=="WALK"
