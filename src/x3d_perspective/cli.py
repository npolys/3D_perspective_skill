"""x3d-perspective: take the user's perspective on an X3D scene. Every command prints JSON.

    x3d-perspective frame SCENE
    x3d-perspective see SCENE [--viewpoint DEF] [--renderer x_ite|x3dom] [--size 1280x720]
    x3d-perspective resolve SCENE "that box" [--viewpoint DEF]
    x3d-perspective relate SCENE FIGURE GROUND [--viewpoint DEF]
    x3d-perspective place SCENE FIGURE "right of" GROUND [--viewpoint DEF] [--gap 0.1]
    x3d-perspective capture SCENE --renderer x_ite|x3dom [--viewpoint DEF] [--set DEF.field=VALUE ...] --out PNG
"""

import argparse
import json
import math
import sys

import numpy as np

from . import frames, perspective, relations, view, x3d_loader


def _size(text):
    width, height = text.lower().split("x")
    return int(width), int(height)


def _json(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    if isinstance(value, float) and math.isinf(value):
        return None
    raise TypeError(f"not JSON serializable: {type(value)}")


def _perspective(scene, args):
    return perspective.from_viewpoint(scene, args.viewpoint, renderer=args.renderer)


def cmd_frame(scene, args):
    return frames.frame(scene)


def cmd_see(scene, args):
    return view.see(scene, _perspective(scene, args), args.size)


def cmd_resolve(scene, args):
    return relations.resolve(scene, _perspective(scene, args), args.phrase, args.size)


def cmd_relate(scene, args):
    return relations.relations_between(scene, _perspective(scene, args), args.figure, args.ground, args.size)


def cmd_place(scene, args):
    return relations.place(scene, _perspective(scene, args), args.figure, args.relation, args.ground, args.gap, args.size)


def cmd_capture(scene, args):
    from . import imaging, live
    p = _perspective(scene, args)
    changes, notes, imagined_scene = [], [], scene
    for change in args.set or []:
        target, value = change.split("=", 1)
        def_name, field = target.rsplit(".", 1)
        changes.append((def_name, field, value))
        moved = relations.with_translation(imagined_scene, def_name, value) if field == "translation" else None
        if moved is None:
            notes.append(f"the imagined view does not model the change to {def_name}.{field}")
        else:
            imagined_scene = moved
    imagined = view.see(imagined_scene, p, args.size)
    with live.LiveView(args.scene, renderer=args.renderer, size=args.size) as session:
        if args.viewpoint:
            session.bind(args.viewpoint)
        for def_name, field, value in changes:
            session.set_field(def_name, field, value)
        png = session.capture(args.out)
        camera = session.camera()
    colors = {name: next((s.diffuse_color for s in shapes if s.diffuse_color), None)
              for name, shapes in scene.objects().items()}
    seen = imaging.object_boxes(png, colors)
    objects = []
    for o in imagined["objects"]:
        found = seen.get(o["name"])
        if o["name"] not in seen:
            continue
        agrees = None
        if found and o.get("pixel_box"):
            agrees = (imaging.agrees if o.get("visible_fraction") == 1.0 else imaging.within)(o["pixel_box"], found)
        objects.append({"name": o["name"], "status": o.get("status"), "imagined_box": o.get("pixel_box"),
                        "seen": found, "agrees": agrees})
    return {
        "renderer": args.renderer, "viewpoint": p.viewpoint, "png": args.out,
        "camera_m": {"position": [round(float(x), 4) for x in camera["position"]],
                     "forward": [round(float(x), 4) for x in camera["forward"]]},
        "imagined_eye_m": p.summary()["eye_m"], "objects": objects, "notes": notes, "page_errors": session.errors,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="x3d-perspective", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name, func, *extra):
        p = sub.add_parser(name)
        p.add_argument("scene")
        for spec in extra:
            p.add_argument(*spec[0], **spec[1])
        p.add_argument("--viewpoint", help="Viewpoint DEF name (default: the initially bound one)")
        p.add_argument("--renderer", default="spec", choices=["spec", "x_ite", "x3dom"])
        p.add_argument("--size", type=_size, default=view.DEFAULT_SIZE, help="view size, default 1280x720")
        p.set_defaults(func=func)
        return p

    command("frame", cmd_frame)
    command("see", cmd_see)
    command("resolve", cmd_resolve, (("phrase",), {}))
    command("relate", cmd_relate, (("figure",), {}), (("ground",), {}))
    command("place", cmd_place, (("figure",), {}), (("relation",), {"choices": relations.RELATIONS}), (("ground",), {}),
            (("--gap",), {"type": float, "default": 0.1}))
    capture = command("capture", cmd_capture, (("--out",), {"required": True}),
                      (("--set",), {"action": "append", "help": "DEF.field=VALUE, applied live before capture"}))
    capture.set_defaults(renderer="x_ite")
    args = parser.parse_args(argv)
    scene = x3d_loader.load(args.scene)
    json.dump(args.func(scene, args), sys.stdout, indent=2, default=_json)
    print()


if __name__ == "__main__":
    main()
