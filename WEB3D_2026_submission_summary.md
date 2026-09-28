# X3D Perspective Skill for Agentic 3D Scene Understanding

## Abstract

We present the X3D Perspective Skill, an agentic reasoning system for taking a user’s perspective on 3D virtual worlds encoded in X3D. The skill models how a browser actually renders a scene from the bound Viewpoint and NavigationInfo, accounting for world units, gravity, camera policy, projection geometry, and viewer-relative spatial semantics. Rather than treating the 3D world as an abstract mesh alone, the system reasons in the same frame as the user: it imagines the image plane, resolves object visibility, estimates layout from the viewer’s perspective, and translates natural language directives such as “put that box to the right of the sphere” into actionable scene edits. The system is designed for interoperability with X3D authoring and runtime tooling, while remaining robust under realistic browser semantics and runtime binding rules.

The project addresses a central challenge in metaverse tooling: enabling embodied AI and agentic assistants to reason correctly about navigation-aware 3D scenes, not merely about geometry in isolation. In X3D, the camera is not a fixed global transform; it depends on binding, navigation mode, avatar size, fieldOfView, viewport aspect ratio, and runtime state. We therefore model scene understanding as a runtime-aware perspective problem, integrating browser semantics with geometric projection and object-level reasoning. This makes the system suitable for conversational 3D workflows, scene verification, automated placement, and live inspection in standards-based virtual worlds.

## Motivation and Problem Statement

Contemporary 3D agents often reason over scenes using generic geometric structures or simplified camera assumptions. In practice, web-based 3D worlds rely on browser- and standards-specific runtime behavior: the currently bound Viewpoint may differ from the first authored node, NavigationInfo may switch camera policy between WALK, FLY, and EXAMINE, and fieldOfView must be interpreted relative to the current viewport aspect ratio. These choices affect the actual rendered image and therefore the validity of any downstream object relations or placement commands.

This challenge is particularly acute in X3D. A browser is a runtime environment with navigation semantics, support detection, gravity, and view framing rules, not just a static scene graph. If an agent ignores the active binding and camera mode, it will reason from the wrong perspective and produce invalid or unsafe spatial instructions. The X3D Perspective Skill addresses this gap by modeling the actual perspective that the browser exposes to a user, and by aligning object reasoning with X3D runtime semantics instead of a simplified geometric camera model.

## Technical Approach

The system is organized as a layered perspective engine. At the core is an X3D scene loader that resolves world-space transforms, units, and object geometry while tracking the currently bound Viewpoint and NavigationInfo. The skill then derives camera state from the active runtime binding, rather than assuming the first encountered node in the file is authoritative. This is a critical design choice because navigation state and viewpoint state can change at runtime and differ from authoring-time defaults.

A key design principle is the separation between document-level X3D correctness and runtime perspective reasoning. We pair the skill with the Web3D Consortium’s x3d_mcp server, which provides authoritative X3D validation, node definitions, defaults, and ontology metadata. This skill, in contrast, owns the runtime perspective model: it takes the browser’s effective camera state, interprets active navigation mode, and calculates the spatial relations the user actually experiences. This division is crucial for agentic 3D reasoning: x3d_mcp answers what is valid in the X3D document; x3d_perspective answers what the user sees from the bound camera and how to act from that view.

The perspective layer models the effective camera pose, including the viewer’s eye position, forward vector, up direction, collision body, and support conditions. It distinguishes among WALK, FLY, EXAMINE, and authored non-grounded camera states. In WALK mode, the skill accounts for gravity and support settling; in FLY mode it preserves a persistent world up; in EXAMINE mode it uses a target-centered orbit policy rather than treating the scene as a grounded walk. This separation is essential for validity: the same object arrangement can imply different viewer-relative relations depending on the active navigation mode.

The projection layer then computes the image plane using the bound Viewpoint fieldOfView and the active viewport dimensions. We implement the X3D rectangular-projection rule: for a rectangular display, the horizontal and vertical field-of-view angles satisfy

width / height = tan(FOVhorizontal / 2) / tan(FOVvertical / 2).

This ensures the camera model matches browser semantics for both landscape and portrait layouts and prevents incorrect assumptions of square or symmetric projection. The image model is then used to project object bounds, compute screen-space boxes, estimate visibility and occlusion, and produce reasoning traces such as object cut-off, depth ordering, and view-relative placement.

To support larger scenes and interactive use, the system incorporates a conservative BVH (bounding volume hierarchy) acceleration structure for raycasts and visibility queries. The BVH is activated only when it is likely to produce a net benefit, reducing overhead on small scenes while improving performance on large or clustered geometry. Runtime controls expose BVH thresholds and configuration through environment variables and CLI flags, and instrumentation emits JSON metrics for profiling and debugging.

## Agentic 3D Reasoning and Scene Interaction

A distinctive feature of the skill is its support for agentic, natural-language 3D interaction. The system can:

- imagine the view the user sees from a specific bound Viewpoint,
- estimate which visible objects are in-frame and how they are arranged,
- resolve viewer-relative instructions such as “left of,” “in front of,” or “above,”
- compute field edits needed to place an object relative to another in the scene,
- compare the predicted view against a live browser capture and detect disagreement.

This turns perspective-taking from a geometric exercise into a practical interface for 3D scene editing and metaverse interaction. In a tool-using agent, the system can serve as the spatial reasoning layer behind commands like “put that box to the right of the sphere,” giving not only a semantic relation but a concrete change in the scene graph. By tying that output to X3D runtime semantics, the skill produces edits that are grounded in the view the user actually sees.

## Security, Safety, and Robustness

The project emphasizes safe operation in live browser-based workflows. Chromium launches are restricted by default, and the system requires explicit opt-in for sandbox-disabled execution in constrained environments. This reduces risk in multi-tenant and security-sensitive settings while still enabling CI and controlled deployment configurations. Additionally, the perspective and verification logic is intentionally conservative: it prefers geometry and runtime semantics over brittle image-only heuristics and keeps fallback checks to address ambiguous object detection cases.

The result is a tool that is robust to degenerate geometry, variable viewport configuration, and browser discrepancies while maintaining a clear stance on unsupported or renderer-specific behaviors. This is especially important for metaverse tools, where scenes may come from untrusted sources, may be authored with complex transforms, and may rely on dynamic runtime navigation states.

## Evaluation and Demonstration

We validate the system through automated tests, runtime-focused regression tests, and browser-based checks. The suite covers navigation mode distinctions, projection correctness under varying aspect ratios, and BVH correctness/performance. A dedicated regression test asserts the X3D rectangular FOV rule for both width > height and height > width. The project also includes validation of runtime binding behavior for Viewpoint and NavigationInfo, ensuring that the viewer’s effective camera policy is selected from the active browser state rather than static scene order.

The project is designed for real-world usage with standard browser stacks and X3D tooling. It can be embedded in agent workflows, run as a CLI tool, and used in live browser pipelines for scene inspection and verification. This makes it well suited for Web3D and metaverse environments where an agent or assistant must reason about 3D content from the user’s actual perspective.

## Contribution to Web3D and the Metaverse Tools Competition

The X3D Perspective Skill contributes a standards-grounded, runtime-aware approach to 3D scene understanding for intelligent agents. Its contributions are fourfold:

1. Runtime-correct perspective modeling for X3D scenes.
2. Explicit navigation policies for WALK, FLY, and EXAMINE.
3. Spec-faithful projection geometry for rectangular displays and varying viewport aspect ratios.
4. Agentic spatial reasoning that translates high-level instructions into scene edits and verification results.

The system is especially relevant to modern metaverse and Web3D workflows, where the user experience depends on navigation-aware rendering and accurate spatial reasoning. By combining X3D semantics, browser runtime awareness, and geometric projection, the skill helps bridge the gap between 3D content and intelligent assistants operating on that content.

## Conclusion

The X3D Perspective Skill is a practical, standards-aware foundation for agentic 3D understanding in X3D scenes. It treats the browser-rendered view as the primary object of reasoning and models the camera as a dynamic, runtime-bound construct instead of as a fixed global transform. This makes it more faithful to real user experience and substantially more useful for scene comprehension, live verification, and semantic editing in immersive web environments.

The work is intended not simply as a geometry library, but as a usable spatial intelligence layer for next-generation metaverse tools, AI assistants, and browser-based 3D authoring workflows.
