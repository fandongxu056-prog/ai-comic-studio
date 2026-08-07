"""Stage 1 LangGraph — Script review loop.

Implements:
  ScriptWriter (author) → [DramaCritic + StyleGuard] (parallel review) → merge → decision
  Decision: approve → complete | needs_revision → loop back | escalate → human

Design reference: docs/agent-collaboration-protocol.md §2
"""

from typing import TypedDict

from langgraph.graph import StateGraph, END


class ScriptReviewState(TypedDict):
    """State that flows through the Stage 1 review graph."""
    project_id: str
    iteration: int
    max_iterations: int
    script: dict  # Current script draft
    drama_critic_feedback: dict | None
    style_guard_feedback: dict | None
    merged_verdict: str  # approved | approved_with_minor | needs_revision | escalated
    merged_score: int
    blocker_count: int
    review_history: list[dict]
    error: str | None


def build_stage1_graph(
    writer,       # ScriptWriterAgent
    critic,       # DramaCriticAgent
    style_guard,  # StyleGuardAgent
) -> StateGraph:
    """Build the LangGraph for Stage 1 script review loop."""

    graph = StateGraph(ScriptReviewState)

    async def generate_draft(state: ScriptReviewState) -> ScriptReviewState:
        """Node: Generate script draft (first iteration only)."""
        if state["iteration"] == 1:
            # This would call writer.execute() with actual data
            pass
        return state

    async def parallel_review(state: ScriptReviewState) -> ScriptReviewState:
        """Node: Run DramaCritic and StyleGuard in parallel."""
        script = state["script"]

        # Parallel reviews
        drama_result = await critic.execute({"script": script})
        style_result = await style_guard.execute({"script": script})

        state["drama_critic_feedback"] = drama_result
        state["style_guard_feedback"] = style_result
        return state

    async def merge_reviews(state: ScriptReviewState) -> ScriptReviewState:
        """Node: Merge parallel reviews into unified verdict."""
        drama = state.get("drama_critic_feedback", {})
        style = state.get("style_guard_feedback", {})

        # Merge issues (dedup by location)
        all_issues = drama.get("critical_issues", []) + style.get("critical_issues", [])
        seen_locations = set()
        deduped = []
        for issue in all_issues:
            loc = issue.get("location", "")
            if loc not in seen_locations:
                deduped.append(issue)
                seen_locations.add(loc)

        # Average scores
        drama_score = drama.get("total_score", 0)
        style_score = style.get("total_score", 0)
        merged_score = round((drama_score + style_score) / 2)

        blocker_count = sum(
            1 for i in deduped if i.get("severity", "") == "blocker"
        )

        # Determine merged verdict
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

    async def revise_draft(state: ScriptReviewState) -> ScriptReviewState:
        """Node: Writer revises based on feedback."""
        # Writer incorporates feedback
        state["iteration"] += 1
        return state

    async def escalate_to_human(state: ScriptReviewState) -> ScriptReviewState:
        """Node: Escalate to human for decision."""
        state["merged_verdict"] = "escalated"
        return state

    # Routing function
    def decide_next(state: ScriptReviewState) -> str:
        """Route based on merged verdict."""
        verdict = state["merged_verdict"]
        if verdict == "approved" or verdict == "approved_with_minor":
            return "complete"
        elif verdict == "needs_revision":
            return "revise"
        else:
            return "escalate"

    # Add nodes
    graph.add_node("generate", generate_draft)
    graph.add_node("review", parallel_review)
    graph.add_node("merge", merge_reviews)
    graph.add_node("revise", revise_draft)
    graph.add_node("escalate", escalate_to_human)

    # Set entry
    graph.set_entry_point("generate")

    # Add edges
    graph.add_edge("generate", "review")
    graph.add_edge("review", "merge")
    graph.add_conditional_edges("merge", decide_next, {
        "complete": END,
        "revise": "revise",
        "escalate": "escalate",
    })
    graph.add_edge("revise", "review")  # Loop back
    graph.add_edge("escalate", END)

    return graph


def create_stage1_graph():
    """Factory to create a compiled Stage 1 graph."""
    from app.agents.stage1_script.writer import ScriptWriterAgent
    from app.agents.stage1_script.critic import DramaCriticAgent
    from app.agents.stage1_script.style_guard import StyleGuardAgent

    writer = ScriptWriterAgent()
    critic = DramaCriticAgent()
    style_guard = StyleGuardAgent()

    graph = build_stage1_graph(writer, critic, style_guard)
    return graph.compile()
