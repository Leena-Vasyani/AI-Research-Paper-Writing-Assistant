"""Compatibility package that forwards `fine_tuning.*` imports to `backend/fine_tuning`.
"""

from pathlib import Path

_backend_pkg = Path(__file__).resolve().parent.parent / "backend" / "fine_tuning"
if _backend_pkg.exists():
    __path__.append(str(_backend_pkg))
