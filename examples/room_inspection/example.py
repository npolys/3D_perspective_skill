"""Take the user's perspective in room.x3d from each Viewpoint, and put the table right of the lamp.

    python examples/room_inspection/example.py           # imagine only
    python examples/room_inspection/example.py --live    # also verify against X_ITE and X3DOM (needs the live extra)
"""

import argparse
from pathlib import Path

import x3d_perspective as xp

ROOM = Path(__file__).with_name("room.x3d")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="verify against X_ITE and X3DOM, keeping the captures")
    args = parser.parse_args()

    scene = xp.load(ROOM)
    frame = xp.frame(scene)
    print(f"up {frame['up']}, units {frame['units']['source']}, navigation {frame['navigation']['type']}")

    for viewpoint in scene.viewpoints:
        for renderer in ("x_ite", "x3dom"):
            p = xp.from_viewpoint(scene, viewpoint.name, renderer=renderer)
            seen = {o["name"]: o for o in xp.see(scene, p)["objects"]}
            box = xp.resolve(scene, p, "that box")["match"]
            sphere = xp.resolve(scene, p, "the sphere")["match"]
            plan = xp.place(scene, p, box, "right of", sphere)
            print(f"\n{viewpoint.name} in {renderer}: eye {p.summary()['eye_m']}")
            for name in (box, sphere):
                print(f"  {name:6s} {seen[name]['status']:8s} box {seen[name].get('pixel_box')}")
            right = [round(x, 3) for x in plan["direction_world"]]
            print(f"  'put {box} right of {sphere}': right is {right} -> {plan['set_field']}")

    if args.live:
        from x3d_perspective import verify
        out = Path("captures")
        report = verify.verify(ROOM, out_dir=out)
        print(f"\nverify: {'all agree' if report['ok'] else 'DISAGREEMENTS'}; captures in {out.resolve()}")
        for result in report["results"]:
            for problem in result["problems"]:
                print(f"  {result['renderer']} {result['viewpoint']}: {problem}")


if __name__ == "__main__":
    main()
