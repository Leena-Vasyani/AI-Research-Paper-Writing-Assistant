"""
LangGraph orchestration runtime for the multi-agent research pipeline.

This package hosts the shared state model (`state.py`), the model-tier
selectors (`models.py`), the graph builder (`graph.py`), and the per-agent
node adapters (`nodes/`).

Pipeline (PDR / architecture diagrams):

    Search -> Topic Mining -> Outline -> Drafting -> Review (revision loop) ->
    Citation -> Formatter

The graph is a state machine over `PipelineState`; the Review node feeds a
conditional edge that loops back to Drafting until quality thresholds pass or
the revision budget is exhausted.
"""

from backend.runtime.state import PipelineState, new_state
from backend.runtime.graph import build_pipeline_graph, run_pipeline

__all__ = [
    "PipelineState",
    "new_state",
    "build_pipeline_graph",
    "run_pipeline",
]
