from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from ai_sdr.outreach.reviewer import review_draft
from ai_sdr.outreach.writer import write_first_touch
from ai_sdr.research.profile import generate_research_profile
from ai_sdr.schemas import OutreachMessageDraft, OutreachReview, OutreachWorkflowRun, ResearchProfile


class OutreachGraphState(TypedDict, total=False):
    """State passed between outreach orchestration nodes."""

    query: str
    top_k: int
    metadata_filter: dict[str, Any] | None
    profile: ResearchProfile | None
    draft: OutreachMessageDraft
    review: OutreachReview
    error: str


def _research_node(state: OutreachGraphState) -> OutreachGraphState:
    profile = generate_research_profile(
        query=state["query"],
        top_k=state.get("top_k", 3),
        metadata_filter=state.get("metadata_filter"),
    )
    if profile is None:
        return {"profile": None, "error": "No matching lead memory records found."}
    return {"profile": profile}


def _route_after_research(state: OutreachGraphState) -> Literal["write", "end"]:
    if state.get("error") or state.get("profile") is None:
        return "end"
    return "write"


def _write_node(state: OutreachGraphState) -> OutreachGraphState:
    profile = state.get("profile")
    if profile is None:
        return {"error": "Cannot write outreach without a research profile."}
    return {"draft": write_first_touch(profile)}


def _review_node(state: OutreachGraphState) -> OutreachGraphState:
    profile = state.get("profile")
    draft = state.get("draft")
    if profile is None or draft is None:
        return {"error": "Cannot review outreach without a profile and draft."}
    return {"review": review_draft(draft, profile)}


def build_outreach_graph():
    """Build the LangGraph workflow for research -> write -> review."""
    graph = StateGraph(OutreachGraphState)
    graph.add_node("research", _research_node)
    graph.add_node("write", _write_node)
    graph.add_node("review", _review_node)

    graph.set_entry_point("research")
    graph.add_conditional_edges(
        "research",
        _route_after_research,
        {"write": "write", "end": END},
    )
    graph.add_edge("write", "review")
    graph.add_edge("review", END)
    return graph.compile()


def run_langgraph_outreach_workflow(
    query: str,
    top_k: int = 3,
    metadata_filter: dict[str, Any] | None = None,
) -> OutreachWorkflowRun | None:
    result = build_outreach_graph().invoke(
        {
            "query": query,
            "top_k": top_k,
            "metadata_filter": metadata_filter,
        }
    )
    profile = result.get("profile")
    draft = result.get("draft")
    review = result.get("review")
    if profile is None or draft is None or review is None:
        return None
    return OutreachWorkflowRun(
        query=query,
        profile=profile,
        draft=draft,
        review=review,
    )
