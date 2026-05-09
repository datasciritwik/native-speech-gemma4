from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes.extract import extract_pdf
from .nodes.screen import run_screener
from .nodes.anatomy import run_anatomy
from .nodes.triage import run_triage
from .nodes.skeptic import run_skeptic
from .nodes.transform import run_transform
from .nodes.verdict import run_verdict
from .nodes.persist import run_persist


def build_ingestion_graph() -> StateGraph:
    """Build the full paper ingestion graph with conditional routing for early exits."""

    graph = StateGraph(AgentState)

    # Add all nodes
    graph.add_node("extract", extract_pdf)
    graph.add_node("screen", run_screener)
    graph.add_node("anatomy", run_anatomy)
    graph.add_node("triage", run_triage)
    graph.add_node("skeptic", run_skeptic)
    graph.add_node("transform", run_transform)
    graph.add_node("verdict", run_verdict)
    graph.add_node("persist", run_persist)
    graph.add_node("skip_to_verdict", _skip_to_verdict)

    # Entry point
    graph.set_entry_point("extract")
    graph.add_edge("extract", "screen")

    # Conditional routing after screener
    graph.add_conditional_edges(
        "screen",
        _route_after_screen,
        {
            "anatomy": "anatomy",
            "skip": "skip_to_verdict",
            "archive": "persist",
        },
    )

    # Normal flow
    graph.add_edge("anatomy", "triage")
    graph.add_edge("triage", "skeptic")
    graph.add_edge("skeptic", "transform")
    graph.add_edge("transform", "verdict")
    graph.add_edge("verdict", "persist")
    graph.add_edge("skip_to_verdict", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


def _route_after_screen(state: AgentState) -> str:
    screener = state.get("screener", {})
    relevance = screener.get("relevance", "irrelevant")

    if relevance == "irrelevant":
        return "archive"
    elif relevance in ("relevant", "paradigm_shift"):
        return "anatomy"
    return "skip"


def _skip_to_verdict(state: AgentState) -> AgentState:
    """Set a default ignore verdict for papers that skip to verdict."""
    from .state import ActionPlan
    screener = state.get("screener", {})
    state["verdict"] = ActionPlan(
        verdict="ignore",
        summary=f"Screener rejected: {screener.get('reason', 'Not relevant')}",
        concrete_steps=[],
        trigger_condition=None,
        scoped_reading=None,
    )
    state["current_stage"] = "persist"
    return state


# Convenience: build the graph at import time
ingestion_graph = build_ingestion_graph()
