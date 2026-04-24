"""Compatibility launcher for the legacy Streamlit entrypoint.

Canonical location: scripts/research_paper.py
"""

from pathlib import Path
import runpy

SCRIPT = Path(__file__).resolve().parent / "scripts" / "research_paper.py"
runpy.run_path(str(SCRIPT), run_name="__main__")
