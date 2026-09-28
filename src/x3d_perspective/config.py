"""Runtime configuration for x3d_perspective.

Provides a small mutable config object that reads defaults from the environment but
can be changed at runtime by applications (CLI, tests, or other embedding code).

This replaces scattered env-reading across modules and allows programmatic control
of BVH hot-path enablement and threshold.
"""
from __future__ import annotations

import os
from typing import Dict, Any


# Default keys and env var names
BVH_ENABLED_ENV = "X3D_PERSPECTIVE_BVH_ENABLED"
BVH_THRESHOLD_ENV = "X3D_PERSPECTIVE_BVH_THRESHOLD"
BVH_METHOD_ENV = "X3D_PERSPECTIVE_BVH_METHOD"
BVH_LEAF_ENV = "X3D_PERSPECTIVE_BVH_LEAF"


def _bool_from_env(val: str | None, default: bool) -> bool:
    if val is None:
        return default
    return str(val).lower() in ("1", "true", "yes")


def _int_from_env(val: str | None, default: int) -> int:
    try:
        return int(val) if val is not None else default
    except Exception:
        return default


# module-level mutable config used by the package
_config: Dict[str, Any] = {
    "bvh_enabled": _bool_from_env(os.environ.get(BVH_ENABLED_ENV), True),
    "bvh_threshold": _int_from_env(os.environ.get(BVH_THRESHOLD_ENV), 2000),
    "bvh_method": os.environ.get(BVH_METHOD_ENV) or "median",
    "bvh_leaf": _int_from_env(os.environ.get(BVH_LEAF_ENV), 24),
    # instrumentation toggle
    "bvh_instrument": _bool_from_env(os.environ.get('X3D_PERSPECTIVE_BVH_INSTRUMENT'), False),
}


def get_config() -> Dict[str, Any]:
    """Return the live config dict (a shallow copy)."""
    return dict(_config)


def set_bvh(enabled: bool | None = None, threshold: int | None = None, method: str | None = None, leaf: int | None = None) -> None:
    """Set BVH-related runtime options. None means leave unchanged.

    This is safe to call at runtime; modules that consult get_bvh_config will observe
    the new values on their next call.
    """
    if enabled is not None:
        _config["bvh_enabled"] = bool(enabled)
    if threshold is not None:
        _config["bvh_threshold"] = int(threshold)
    if method is not None:
        _config["bvh_method"] = str(method)
    if leaf is not None:
        _config["bvh_leaf"] = int(leaf)


def get_bvh_config() -> Dict[str, Any]:
    """Return the BVH-related config values."""
    return {"enabled": _config["bvh_enabled"], "threshold": _config["bvh_threshold"], "method": _config["bvh_method"], "leaf": _config["bvh_leaf"]}


# convenience: apply CLI-like args (namespace or dict)
def apply_args(args) -> None:
    """Apply CLI args-like object: looks for attributes 'no_bvh' and 'bvh_threshold', 'bvh_method', 'bvh_leaf'."""
    if getattr(args, "no_bvh", False):
        set_bvh(enabled=False)
    if getattr(args, "bvh_threshold", None) is not None:
        set_bvh(threshold=getattr(args, "bvh_threshold"))
    if getattr(args, "bvh_method", None) is not None:
        set_bvh(method=getattr(args, "bvh_method"))
    if getattr(args, "bvh_leaf", None) is not None:
        set_bvh(leaf=getattr(args, "bvh_leaf"))
    # instrumentation flag
    if getattr(args, "bvh_instrument", None) is not None:
        set_instrumentation(bool(getattr(args, "bvh_instrument")))


def set_instrumentation(enabled: bool) -> None:
    """Enable or disable BVH instrumentation at runtime."""
    _config["bvh_instrument"] = bool(enabled)


def get_instrumentation() -> bool:
    return bool(_config.get("bvh_instrument", False))


# File-backed config helpers
def _default_config_path() -> str:
    """Return the default per-user config file path.

    Honors XDG_CONFIG_HOME if set, otherwise uses ~/.config/x3d_perspective/config.json
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return os.path.join(xdg, "x3d_perspective", "config.json")
    home = os.path.expanduser("~")
    return os.path.join(home, ".config", "x3d_perspective", "config.json")


def load_config_file(path: str | None = None) -> bool:
    """Load configuration from the given JSON file (or the default per-user file if None).

    Returns True if a file was found and loaded, False otherwise. Merges read values into
    the in-memory config; values in the file are overridden by subsequent calls to apply_args.
    """
    import json
    if path is None:
        path = _default_config_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return False
    except Exception:
        # don't raise for malformed files; act as if not present
        return False
    # merge known keys
    if "bvh_enabled" in data:
        try:
            _config["bvh_enabled"] = bool(data["bvh_enabled"])
        except Exception:
            pass
    if "bvh_threshold" in data:
        try:
            _config["bvh_threshold"] = int(data["bvh_threshold"])
        except Exception:
            pass
    if "bvh_method" in data:
        _config["bvh_method"] = str(data["bvh_method"])
    if "bvh_leaf" in data:
        try:
            _config["bvh_leaf"] = int(data["bvh_leaf"])
        except Exception:
            pass
    if "bvh_instrument" in data:
        try:
            _config["bvh_instrument"] = bool(data["bvh_instrument"])
        except Exception:
            pass
    return True


def save_config_file(path: str | None = None) -> bool:
    """Write the current runtime config to the given JSON file (or default per-user file if None).

    Creates parent directories as needed. Returns True on success, False on failure.
    """
    import json
    import errno
    if path is None:
        path = _default_config_path()
    d = get_config()
    parent = os.path.dirname(path)
    try:
        os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=2)
        return True
    except Exception:
        return False
