# Contributing

Thank you for helping improve `x3d-perspective`. Issues and pull requests are welcome at <https://github.com/npolys/3D_perspective_skill>.

## Set up

```
git clone https://github.com/npolys/3D_perspective_skill
cd 3D_perspective_skill
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev,live]"        # Windows: .venv\Scripts\python
.venv/bin/python -m playwright install chromium
```

## Before you open a pull request

```
ruff check src tests scripts
pytest                 # offline tests
pytest --live          # live tests in X_ITE and X3DOM, if you changed projection, perspective, live or imaging code
```

Keep the style of the surrounding code: short functions with a docstring, and no speculative abstractions.

## Ground every X3D claim

The value of this project is that its rules are right about X3D. When you add or change one:

- **Cite the clause.** Quote the X3D specification and give its clause, as `docs/X3D_MAPPINGS.md` does. Check the wording in the current version (4.1).
- **Take defaults and field types from x3d_mcp,** through `describe_node` and the snapshot in `src/x3d_perspective/data/x3d_defaults.json`. Don't take them from memory.
- **Confirm behaviour by rendering.** Predict the pixels first, then capture the view in both X_ITE and X3DOM and compare. Where the renderers differ, record the measured behaviour, as `SETTLES_ON_BIND` in `perspective.py` does, and add a live test.
- **Leave X3D correctness to x3d_mcp:** schema and DTD validation, ontology terms, node definitions. Don't vendor those files here. Propose changes to x3d_mcp upstream; see `upstream/x3d_mcp/`.

## Adding a test scene

Put it under `examples/` or build it in a test with `conftest.write_scene`. For live checks, follow the authoring guidance in [docs/TESTING.md](docs/TESTING.md#verifying-your-own-scenes): distinct saturated colours, DEF'd Transforms, and WALK Viewpoints over support.

## Releasing

1. Update `__version__` in `src/x3d_perspective/__init__.py` and add a section to `CHANGELOG.md`.
2. Run the full suite with `pytest --live` and `ruff check`.
3. Build and check the package with `python -m build`, then `twine check dist/*`.
4. Tag the release (`git tag v7.0.0`) and push the tag.

## License

By contributing, you agree that your contributions are licensed under the project's [LICENSE](LICENSE), the Web3D Consortium Open-Source License for Models and Software.
