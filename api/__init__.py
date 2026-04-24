"""Compatibility package that forwards `api.*` imports to `backend/api`.

This allows existing commands like `uvicorn api.main:app` to keep working
while the canonical backend code lives under `backend/`.
"""

from pathlib import Path

_backend_pkg = Path(__file__).resolve().parent.parent / "backend" / "api"
if _backend_pkg.exists():
    __path__.append(str(_backend_pkg))
