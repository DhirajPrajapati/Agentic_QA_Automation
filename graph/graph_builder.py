"""
graph_builder — Builds the LangGraph pipeline (Phase 4: full graph).
Part of: QA Orchestrator
Phase: 4
Mock-safe: yes
"""
from langgraph.graph import END, StateGraph

from agents.analysis_agent import analysis_node
from agents.api_agent import api_node
from agents.orchestrator_agent import orchestrator_node
from agents.playwright_agent import playwright_node
from agents.reporter_agent import reporter_node
from agents.test_case_agent import test_case_node
from agents.test_script_agent import test_script_node
from graph.edges import route_after_playwright, route_after_scripts
from graph.state import QAState


def build_graph():
    """Compile the Phase 4 QA pipeline graph with conditional routing."""
    g = StateGraph(QAState)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("analysis", analysis_node)
    g.add_node("test_case", test_case_node)
    g.add_node("test_script", test_script_node)
    g.add_node("playwright", playwright_node)
    g.add_node("api", api_node)
    g.add_node("reporter", reporter_node)

    g.set_entry_point("orchestrator")
    g.add_edge("orchestrator", "analysis")
    g.add_edge("analysis", "test_case")
    g.add_edge("test_case", "test_script")

    g.add_conditional_edges(
        "test_script",
        route_after_scripts,
        {"ui_only": "playwright", "both": "playwright"},
    )
    g.add_conditional_edges(
        "playwright",
        route_after_playwright,
        {"run_api": "api", "report": "reporter"},
    )
    g.add_edge("api", "reporter")
    g.add_edge("reporter", END)

    return g.compile()
