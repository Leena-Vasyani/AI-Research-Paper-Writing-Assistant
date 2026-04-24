from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _has_spec(module_name: str) -> bool:
    return find_spec(module_name) is not None


class TestSmokeImports(unittest.TestCase):
    def test_backend_module_discoverability(self) -> None:
        # Discoverability checks avoid importing heavy modules while still validating layout.
        self.assertTrue(_has_spec("backend"))
        self.assertTrue(_has_spec("backend.api"))
        self.assertTrue(_has_spec("backend.api.main"))
        self.assertTrue(_has_spec("backend.core_agents"))
        self.assertTrue(_has_spec("backend.fine_tuning"))

    def test_compatibility_package_discoverability(self) -> None:
        self.assertTrue(_has_spec("api"))
        self.assertTrue(_has_spec("core_agents"))
        self.assertTrue(_has_spec("fine_tuning"))

    def test_launcher_files_exist(self) -> None:
        expected = [
            ROOT / "run.bat",
            ROOT / "research_paper.py",
            ROOT / "scripts" / "run.bat",
            ROOT / "scripts" / "research_paper.py",
        ]
        for file_path in expected:
            self.assertTrue(file_path.exists(), f"Missing expected launcher: {file_path}")

    def test_root_launchers_delegate_to_scripts(self) -> None:
        run_bat_text = (ROOT / "run.bat").read_text(encoding="ascii", errors="ignore").lower()
        self.assertIn("scripts\\run.bat", run_bat_text)

        research_py_text = (ROOT / "research_paper.py").read_text(encoding="utf-8").lower()
        self.assertIn("scripts/research_paper.py", research_py_text)
        self.assertIn("runpy.run_path", research_py_text)


if __name__ == "__main__":
    unittest.main()
