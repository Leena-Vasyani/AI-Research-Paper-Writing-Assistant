"""
Phase 7 tests for the pipeline controller (HITL stage stepping).

Offline: the outline accessor is patched to run without an LLM.
"""

import unittest

import backend.runtime.nodes.outline as outline_mod
from backend.api.controllers import pipeline_controller as pc
from backend.core_agents.outline_agent import OutlineAgent
from backend.runtime.state import new_state


class PipelineControllerTest(unittest.TestCase):
    def test_stage_order(self):
        self.assertEqual(
            pc.STAGE_ORDER,
            ["search", "topic_mining", "outline", "drafting", "review", "citation", "formatter"],
        )

    def test_unknown_stage_raises(self):
        with self.assertRaises(ValueError):
            pc.run_stage("nope", {"topic": "x"})

    def test_run_outline_stage_offline(self):
        orig = outline_mod.outline_agent
        outline_mod.outline_agent = lambda: OutlineAgent(use_llm=False)
        try:
            state = dict(new_state("smart grid forecasting"))
            state["themes"] = {"clusters": [{"theme": "load forecasting"}], "gaps": []}
            merged = pc.run_stage("outline", state)
            self.assertIn("blueprint", merged)
            self.assertTrue(merged["blueprint"]["sections"])
            # original inputs preserved
            self.assertEqual(merged["topic"], "smart grid forecasting")
            # timing recorded for the stage
            self.assertIn("outline", merged.get("stage_timings", {}))
        finally:
            outline_mod.outline_agent = orig

    def test_warnings_accumulate(self):
        state = dict(new_state("t"))
        state["warnings"] = ["existing warning"]
        # formatter stage on an empty draft should still merge, preserving warnings
        merged = pc.run_stage("formatter", state)
        self.assertIn("existing warning", merged["warnings"])


if __name__ == "__main__":
    unittest.main()
