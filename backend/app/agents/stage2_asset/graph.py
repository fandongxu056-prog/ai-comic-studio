"""Stage 2 LangGraph — Asset Design review loop.

Implements parallel design + centralized audit pattern (from agent-collaboration-protocol.md §3):
  [CharDesigner | SceneDesigner | PropDesigner] → ConsistencyAuditor → merge → decide

Key difference from Stage 1:
- 3 parallel Authors (not 1) — each designs independently
- 1 centralized Reviewer (not 2 parallel) — consistency must be checked holistically
"""

from typing import TypedDict

from langgraph.graph import StateGraph, END


class AssetReviewState(TypedDict, total=False):
    """State flowing through Stage 2 review graph."""
    project_id: str
    iteration: int
    max_iterations: int

    # Design outputs (from 3 parallel authors)
    characters: list[dict]
    locations: list[dict]
    props: list[dict]
    style_manifest: dict

    # Review output (from ConsistencyAuditor)
    audit_feedback: dict | None

    # Merged decision
    merged_verdict: str
    merged_score: int
    blocker_count: int

    # Script data (for coverage checks)
    script: dict
    style_preference: dict
    consistency_requirements: dict

    review_history: list[dict]
    error: str | None


def build_stage2_graph(
    char_designer,         # CharacterDesignerAgent
    scene_designer,        # SceneDesignerAgent
    prop_designer,         # PropDesignerAgent
    consistency_auditor,   # ConsistencyAuditorAgent
) -> StateGraph:
    """Build the LangGraph for Stage 2 asset design review loop."""

    graph = StateGraph(AssetReviewState)

    async def parallel_design(state: AssetReviewState) -> AssetReviewState:
        """Run all 3 designer agents in parallel.

        Each designer reads the script and style preferences independently.
        They do NOT read each other's outputs — that's the auditor's job.
        """
        script = state.get("script", {})
        style_pref = state.get("style_preference", {})
        consistency = state.get("consistency_requirements", {})

        common_input = {
            "project_id": state["project_id"],
            "script": script,
            "style_preference": style_pref,
            "consistency_requirements": consistency,
        }

        # Run all three in parallel
        char_result = await char_designer.execute(common_input)
        scene_result = await scene_designer.execute(common_input)
        prop_result = await prop_designer.execute(common_input)

        state["characters"] = char_result.get("characters", [])
        state["locations"] = scene_result.get("locations", [])
        state["props"] = prop_result.get("props", [])

        # Store style manifest from character designer (shared across all)
        state["style_manifest"] = char_result.get("style_manifest", {})

        return state

    async def audit_designs(state: AssetReviewState) -> AssetReviewState:
        """Run ConsistencyAuditor on all three design outputs simultaneously.

        The auditor receives ALL assets at once — this is critical because
        cross-asset consistency issues can only be detected holistically.
        """
        audit_input = {
            "characters": state.get("characters", []),
            "locations": state.get("locations", []),
            "props": state.get("props", []),
            "style_manifest": state.get("style_manifest", {}),
            "script": state.get("script", {}),
        }

        result = await consistency_auditor.execute(audit_input)
        state["audit_feedback"] = result
        return state

    async def merge_and_decide(state: AssetReviewState) -> AssetReviewState:
        """Process audit feedback into a verdict."""
        feedback = state.get("audit_feedback", {})

        state["merged_score"] = feedback.get("total_score", 0)
        state["blocker_count"] = sum(
            1 for i in feedback.get("critical_issues", [])
            if i.get("severity") == "blocker"
        )

        total = state["merged_score"]
        blockers = state["blocker_count"]

        if total >= 80 and blockers == 0:
            state["merged_verdict"] = "approved"
        elif 65 <= total < 80 and blockers == 0:
            state["merged_verdict"] = "approved_with_minor"
        elif state["iteration"] >= state["max_iterations"]:
            state["merged_verdict"] = "escalated"
        else:
            state["merged_verdict"] = "needs_revision"

        # Append to review history
        history = state.get("review_history", [])
        history.append({
            "round": state["iteration"],
            "reviewer": "consistency_auditor_v1",
            "verdict": state["merged_verdict"],
            "total_score": total,
            "blocker_count": blockers,
        })
        state["review_history"] = history

        return state

    async def revise_designs(state: AssetReviewState) -> AssetReviewState:
        """Revise designs based on audit feedback.

        Each designer receives the audit feedback and revises its own output.
        Only minor/major issues are auto-fixed; blockers trigger escalation.
        """
        feedback = state.get("audit_feedback", {})
        state["iteration"] += 1

        # Each designer revises independently
        from app.agents.base import ReviewFeedback
        fb = ReviewFeedback(**feedback) if isinstance(feedback, dict) else feedback

        if state.get("characters"):
            char_input = {"characters": state["characters"]}
            char_revised = await char_designer.revise(fb, char_input)
            if char_revised.get("status") != "escalated":
                state["characters"] = char_revised.get("characters", state["characters"])

        if state.get("locations"):
            loc_input = {"locations": state["locations"]}
            loc_revised = await scene_designer.revise(fb, loc_input)
            if loc_revised.get("status") != "escalated":
                state["locations"] = loc_revised.get("locations", state["locations"])

        return state

    async def escalate_to_human(state: AssetReviewState) -> AssetReviewState:
        """Escalate unresolved blockers to human."""
        state["merged_verdict"] = "escalated"
        return state

    # ── Graph structure ──

    graph.add_node("design", parallel_design)
    graph.add_node("audit", audit_designs)
    graph.add_node("merge", merge_and_decide)
    graph.add_node("revise", revise_designs)
    graph.add_node("escalate", escalate_to_human)

    graph.set_entry_point("design")

    graph.add_edge("design", "audit")
    graph.add_edge("audit", "merge")

    def route_decision(state: AssetReviewState) -> str:
        verdict = state.get("merged_verdict", "needs_revision")
        if verdict in ("approved", "approved_with_minor"):
            return "complete"
        elif verdict == "needs_revision":
            return "revise"
        return "escalate"

    graph.add_conditional_edges("merge", route_decision, {
        "complete": END,
        "revise": "revise",
        "escalate": "escalate",
    })
    graph.add_edge("revise", "design")  # Loop: revise then re-design
    graph.add_edge("escalate", END)

    return graph


def create_stage2_graph(llm_service=None):
    """Factory to create a compiled Stage 2 graph."""
    from app.agents.stage2_asset.character_designer import CharacterDesignerAgent
    from app.agents.stage2_asset.scene_designer import SceneDesignerAgent
    from app.agents.stage2_asset.prop_designer import PropDesignerAgent
    from app.agents.stage2_asset.consistency_auditor import ConsistencyAuditorAgent

    cd = CharacterDesignerAgent(llm_service=llm_service)
    sd = SceneDesignerAgent(llm_service=llm_service)
    pd = PropDesignerAgent()
    ca = ConsistencyAuditorAgent()

    g = build_stage2_graph(cd, sd, pd, ca)
    return g.compile()
