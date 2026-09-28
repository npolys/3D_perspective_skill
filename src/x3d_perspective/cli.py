"""x3d-perspective: take the user's perspective on an X3D scene. Every command prints JSON.

    x3d-perspective frame SCENE
    x3d-perspective see SCENE [--viewpoint DEF] [--renderer x_ite|x3dom] [--size 1280x720]
    x3d-perspective resolve SCENE "that box" [--viewpoint DEF]
    x3d-perspective relate SCENE FIGURE GROUND [--viewpoint DEF]
    x3d-perspective place SCENE FIGURE "right of" GROUND [--viewpoint DEF] [--gap 0.1]
    x3d-perspective capture SCENE --renderer x_ite|x3dom --out PNG [--viewpoint DEF] [--set DEF.field=VALUE ...]
    x3d-perspective verify SCENE [--viewpoint DEF ...] [--renderer x_ite|x3dom ...] [--out-dir DIR]

See docs/CLI.md for every option and output field.
"""

import argparse
import json
import math
import sys

import numpy as np

from . import __version__, frames, perspective, relations, view, x3d_loader

RENDERER_CHOICES = ["spec", "x_ite", "x3dom"]


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
    from . import imaging, live, verify
    if args.renderer == "spec":
        args.renderer = "x_ite"
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
    with live.LiveView(args.scene, renderer=args.renderer, size=args.size, allow_no_sandbox=getattr(args, 'no_sandbox', False)) as session:
        if args.viewpoint:
            session.bind(args.viewpoint)
        for def_name, field, value in changes:
            session.set_field(def_name, field, value)
        png = session.capture(args.out)
        camera = session.camera()
    rows = verify.compare(imagined, imaging.object_boxes(png, verify.object_colors(scene)))
    return {
        "renderer": args.renderer, "viewpoint": p.viewpoint, "png": args.out,
        "camera_m": {"position": [round(float(x), 4) for x in camera["position"]],
                     "forward": [round(float(x), 4) for x in camera["forward"]]},
        "imagined_eye_m": p.summary()["eye_m"], "objects": rows, "notes": notes, "page_errors": session.errors,
    }


def cmd_verify(scene, args):
    from . import live, verify
    return verify.verify(args.scene, args.viewpoint, args.renderer or live.RENDERERS, args.size, args.out_dir,
                         allow_no_sandbox=getattr(args, 'no_sandbox', False))


def _parser():
    parser = argparse.ArgumentParser(prog="x3d-perspective", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    # BVH runtime control: threshold and explicit disable
    parser.add_argument("--bvh-threshold", type=int, help="Enable BVH hot-path when occluder triangle count >= N (default: 2000)")
    parser.add_argument("--no-bvh", action="store_true", help="Disable BVH hot-path regardless of threshold")
    parser.add_argument("--config", help="Path to JSON config file. If omitted, the default per-user config (~/.config/x3d_perspective/config.json) is used when present.")
    parser.add_argument("--bvh-instrument", action="store_true", help="Enable BVH instrumentation (timers/counters) for diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name, func, help_text, *extra, viewpoint=True, renderer=True):
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.add_argument("scene", help="X3D XML (.x3d) file")
        for flags, options in extra:
            p.add_argument(*flags, **options)
        if viewpoint:
            p.add_argument("--viewpoint", help="Viewpoint DEF name (default: the initially bound one)")
        if renderer:
            p.add_argument("--renderer", default="spec", choices=RENDERER_CHOICES,
                           help="whose WALK behaviour to imagine (default: the spec's)")
        p.add_argument("--size", type=_size, default=view.DEFAULT_SIZE, help="view size WxH, default 1280x720")
        p.set_defaults(func=func)
        return p

    command("frame", cmd_frame, "up, gravity, units, extent, body, viewpoints and objects", viewpoint=False, renderer=False)
    command("see", cmd_see, "the imagined view: where each object lands, and whether it is visible")
    command("resolve", cmd_resolve, "which object a phrase such as 'that box' refers to",
            (("phrase",), {"help": "for example 'that box' or a DEF name"}))
    command("relate", cmd_relate, "which relations hold between two objects, from this view",
            (("figure",), {}), (("ground",), {}))
    command("place", cmd_place, "the field change that puts FIGURE in RELATION to GROUND, from this view",
            (("figure",), {}), (("relation",), {"choices": relations.RELATIONS}), (("ground",), {}),
            (("--gap",), {"type": float, "default": 0.1, "help": "clearance in meters, default 0.1"}))
    command("capture", cmd_capture, "capture the live view in X_ITE or X3DOM and compare it with the imagined view",
            (("--out",), {"required": True, "help": "PNG file to write"}),
            (("--set",), {"action": "append", "metavar": "DEF.field=VALUE", "help": "applied live before capture"}),
            (("--no-sandbox",), {"action": "store_true", "help": "Allow launching Chromium with --no-sandbox (unsafe). Default is to avoid it."}))
    verify = command("verify", cmd_verify, "check every Viewpoint in both renderers; exit status 1 on disagreement",
                    (("--out-dir",), {"help": "keep the captures here"}), (("--no-sandbox",), {"action": "store_true", "help": "Allow launching Chromium with --no-sandbox (unsafe). Default is to avoid it."}), viewpoint=False, renderer=False)
    verify.add_argument("--viewpoint", action="append", help="Viewpoint DEF name; repeat for several (default: all)")
    verify.add_argument("--renderer", action="append", choices=["x_ite", "x3dom"],
                       help="repeat for several (default: both)")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    # Apply BVH CLI options to runtime config so modules can read them programmatically.
    from . import config as _config
    from . import geometry
    # Load config file if provided or default per-user config exists
    if getattr(args, 'config', None) is not None:
        _config.load_config_file(args.config)
    else:
        _config.load_config_file()  # no-op if default file missing
    # Then apply CLI overrides
    _config.apply_args(args)
    scene = x3d_loader.load(args.scene)
    result = args.func(scene, args)
    if _config.get_instrumentation():
        metrics = geometry.get_metrics(reset=True)
        sys.stderr.write(json.dumps({"bvh_metrics": metrics}, default=_json) + "\n")
    json.dump(result, sys.stdout, indent=2, default=_json)
    print()
    if args.command == "verify" and not result["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
