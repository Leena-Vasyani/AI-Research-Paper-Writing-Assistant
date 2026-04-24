"""Compatibility package that forwards `core_agents.*` imports to `backend/core_agents`.
"""

from pathlib import Path

_backend_pkg = Path(__file__).resolve().parent.parent / "backend" / "core_agents"
if _backend_pkg.exists():
    __path__.append(str(_backend_pkg))
