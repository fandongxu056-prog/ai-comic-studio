"""Stage 3 LangGraph — Storyboard review loop.

Pattern: 1 Author → 2 parallel Reviewers → merge → decide
  ShotComposer → [PacingDirector | ContinuityCheck] → merge → approve/revise/escalate

The two reviewers cover orthogonal dimensions:
- PacingDirector: "Will the audience get bored?"
- ContinuityCheck: "Will there be continuity errors?"

Design reference: docs/agent-collaboration-protocol.md §4
"""

from typing import TypedDict

from langgraph.graph import StateGraph, END


class StoryboardReviewState(TypedDict, total=False):
    project_id: str
    iteration: int
    max_iterations: int

    # Shot plan
    shot_plan: dict
    assets: dict
    script: dict
    continuity_rules: list

    # Parallel reviews
    pacing_feedback: dict | None
    continuity_feedback: dict | None

    # Merged
    merged_verdict: str
    merged_score: int
    blocker_count: int

    review_history: list[dict]
    error: str | None


def build_stage3_graph(
    shot_composer,       # ShotComposerAgent
    pacing_director,     # PacingDirectorAgent
    continuity_check,    # ContinuityCheckAgent
) -> StateGraph:
    """Build the LangGraph for Stage 3 storyboard review loop."""

    graph = StateGraph(StoryboardReviewState)

    async def compose_storyboard(state: StoryboardReviewState) -> StoryboardReviewState:
        """Compose the initial shot plan from script + assets."""
        composer_input = {
            "project_id": state["project_id"],
            "script": state.get("script", {}),
            "assets": state.get("assets", {}),
            "target_spec": state.get("target_spec", {}),
            "continuity_rules": state.get("continuity_rules", []),
        }
        result = await shot_composer.execute(composer_input)
        state["shot_plan"] = result
        return state

    async def parallel_review(state: StoryboardReviewState) -> StoryboardReviewState:
        """Run PacingDirector and ContinuityCheck in parallel.

        Both read the same shot_plan but review completely different dimensions.
        """
        shot_plan = state.get("shot_plan", {})

        # Both reviewers get the full context
        review_input = {
            "shot_plan": shot_plan,
            "assets": state.get("assets", {}),
            "script": state.get("script", {}),
            "continuity_rules": state.get("continuity_rules", []),
        }

        # Parallel execution
        pacing_result = await pacing_director.execute(review_input)
        continuity_result = await continuity_check.execute(review_input)

        state["pacing_feedback"] = pacing_result
        state["continuity_feedback"] = continuity_result

        return state

    async def merge_reviews(state: StoryboardReviewState) -> StoryboardReviewState:
        """Merge parallel reviews and determine verdict."""
        pacing = state.get("pacing_feedback", {})
        continuity = state.get("continuity_feedback", {})

        # Collect all issues
        all_issues = (
            pacing.get("critical_issues", []) +
            continuity.get("critical_issues", [])
        )

        # Dedup by shot_id + category
        seen = set()
        deduped = []
        for issue in all_issues:
            key = f"{issue.get('location', '')}:{issue.get('category', '')}"
            if key not in seen:
                deduped.append(issue)
                seen.add(key)

        # Average scores
        pacing_score = pacing.get("total_score", 0)
        continuity_score = continuity.get("total_score", 0)
        merged_score = round((pacing_score + continuity_score) / 2)

        blocker_count = sum(
            1 for i in deduped if i.get("severity") == "blocker"
        )

        # Decision logic
        if merged_score >= 80 and blocker_count == 0:
            verdict = "approved"
        elif 65 <= merged_score < 80 and blocker_count == 0:
            verdict = "approved_with_minor"
        elif state["iteration"] >= state["max_iterations"]:
            verdict = "escalated"
        else:
            verdict = "needs_revision"

        state["merged_score"] = merged_score
        state["blocker_count"] = blocker_count
        state["merged_verdict"] = verdict

        return state

    async def revise_storyboard(state: StoryboardReviewState) -> StoryboardReviewState:
        """ShotComposer revises based on merged feedback."""
        state["iteration"] += 1

        # Build unified feedback from both reviewers
        pacing = state.get("pacing_feedback", {})
        continuity = state.get("continuity_feedback", {})

        from app.agents.base import ReviewFeedback
        unified_issues = (
            pacing.get("critical_issues", []) +
            continuity.get("critical_issues", [])
        )
        # Take the worse verdict
        pacing_verdict = pacing.get("overall_verdict", "approved")
        cont_verdict = continuity.get("overall_verdict", "approved")
        worse_verdict = (
            "needs_revision" if "needs_revision" in (pacing_verdict, cont_verdict)
            else "approved_with_minor" if "approved_with_minor" in (pacing_verdict, cont_verdict)
            else "approved"
        )

        fb = ReviewFeedback(
            overall_verdict=worse_verdict,
            total_score=state["merged_score"],
            dimension_scores={},
            critical_issues=unified_issues,
        )

        revised = await shot_composer.revise(fb, state.get("shot_plan", {}))
        if revised.get("status") != "escalated":
            state["shot_plan"] = revised

        return state

    async def escalate_to_human(state: StoryboardReviewState) -> StoryboardReviewState:
        state["merged_verdict"] = "escalated"
        return state

    # ── Build graph ──

    graph.add_node("compose", compose_storyboard)
    graph.add_node("review", parallel_review)
    graph.add_node("merge", merge_reviews)
    graph.add_node("revise", revise_storyboard)
    graph.add_node("escalate", escalate_to_human)

    graph.set_entry_point("compose")

    graph.add_edge("compose", "review")
    graph.add_edge("review", "merge")

    def route_decision(state: StoryboardReviewState) -> str:
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
    graph.add_edge("revise", "review")  # Loop back: revise then re-review
    graph.add_edge("escalate", END)

    return graph


def create_stage3_graph(llm_service=None):
    """Factory to create a compiled Stage 3 graph."""
    from app.agents.stage3_storyboard.shot_composer import ShotComposerAgent
    from app.agents.stage3_storyboard.pacing_director import PacingDirectorAgent
    from app.agents.stage3_storyboard.continuity_check import ContinuityCheckAgent

    sc = ShotComposerAgent(llm_service=llm_service)
    pd = PacingDirectorAgent()
    cc = ContinuityCheckAgent()

    g = build_stage3_graph(sc, pd, cc)
    return g.compile()
