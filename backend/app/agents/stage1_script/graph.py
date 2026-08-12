"""Stage 1 LangGraph — Script review loop.

Implements:
  ScriptWriter (author) → [DramaCritic + StyleGuard] (parallel review) → merge → decision
  Decision: approve → complete | needs_revision → loop back | escalate → human

Design reference: docs/agent-collaboration-protocol.md §2

Key design choice: LLMService is NOT stored in the TypedDict state (it's non-serializable).
Instead, it flows through closure variables captured by node functions.
"""

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class ScriptReviewState(TypedDict):
    """State that flows through the Stage 1 review graph.

    All values must be JSON-serializable (LangGraph serializes state between nodes).
    The 'llm_service' and agent instances flow through closure capture, not state.
    """
    project_id: str
    iteration: int
    max_iterations: int

    # Input data for the writer
    input_data: dict

    # Current script artifact
    script: dict

    # Review outputs
    drama_critic_feedback: dict | None
    style_guard_feedback: dict | None

    # Merged decision
    merged_verdict: str  # approved | approved_with_minor | needs_revision | escalated
    merged_score: int
    blocker_count: int

    # Audit
    review_history: list[dict]
    error: str | None


def build_stage1_graph(
    writer,         # ScriptWriterAgent (with LLM service injected)
    critic,         # DramaCriticAgent
    style_guard,    # StyleGuardAgent
    llm_service: Any = None,  # LLMService instance for reviewer LLM calls
) -> StateGraph:
    """Build the LangGraph for Stage 1 script review loop.

    The agents and llm_service are captured by closure — they don't go in state.
    """
    # Fallback llm_service (reviewers can use their own if set in constructor)
    reviewer_llm = llm_service

    graph = StateGraph(ScriptReviewState)

    # ── Node: Generate Draft ──

    async def generate_draft(state: ScriptReviewState) -> ScriptReviewState:
        """Generate the initial script draft via Writer Agent."""
        if state["iteration"] != 1:
            return state  # Only generate on first iteration

        try:
            input_data = state.get("input_data", {})
            context = {}  # Writer already has llm_service in constructor

            script = await writer.execute(input_data=input_data, context=context)
            state["script"] = script
        except Exception as e:
            state["error"] = f"Writer generation failed: {e}"
            state["merged_verdict"] = "escalated"

        return state

    # ── Node: Parallel Review ──

    async def parallel_review(state: ScriptReviewState) -> ScriptReviewState:
        """Run DramaCritic and StyleGuard in parallel."""
        script = state.get("script", {})
        input_data = state.get("input_data", {})
        context = {"llm_service": reviewer_llm}  # Pass LLM service for deep review

        try:
            # Run both reviewers concurrently
            import asyncio
            drama_fb, style_fb = await asyncio.gather(
                critic.execute(
                    {"script": script, "project_input": input_data, "style_preference": input_data.get("style_preference", {})},
                    context=context,
                ),
                style_guard.execute(
                    {"script": script, "style_preference": input_data.get("style_preference", {})},
                    context=context,
                ),
            )
            state["drama_critic_feedback"] = drama_fb
            state["style_guard_feedback"] = style_fb
        except Exception as e:
            state["error"] = f"Review failed: {e}"
            # If one reviewer fails, try the other
            if state["drama_critic_feedback"] is None:
                state["drama_critic_feedback"] = {"overall_verdict": "error", "total_score": 0, "critical_issues": []}
            if state["style_guard_feedback"] is None:
                state["style_guard_feedback"] = {"overall_verdict": "error", "total_score": 0, "critical_issues": []}

        return state

    # ── Node: Merge Reviews ──

    async def merge_reviews(state: ScriptReviewState) -> ScriptReviewState:
        """Merge parallel reviews into unified verdict."""
        drama = state.get("drama_critic_feedback", {}) or {}
        style = state.get("style_guard_feedback", {}) or {}

        # Merge issues (dedup by location + category)
        all_issues = drama.get("critical_issues", []) + style.get("critical_issues", [])
        seen_locations = set()
        deduped = []
        for issue in all_issues:
            # Handle both dict (from model_dump) and object
            loc = issue.get("location", "") if isinstance(issue, dict) else issue.location
            cat = issue.get("category", "") if isinstance(issue, dict) else issue.category
            key = (loc, cat)
            if key not in seen_locations:
                deduped.append(issue)
                seen_locations.add(key)

        # Average scores (weighted: DramaCritic 60%, StyleGuard 40% for script stage)
        drama_score = drama.get("total_score", 0)
        style_score = style.get("total_score", 0)
        if drama_score > 0 and style_score > 0:
            merged_score = round(drama_score * 0.6 + style_score * 0.4)
        else:
            merged_score = max(drama_score, style_score)

        blocker_count = sum(
            1 for i in deduped
            if (i.get("severity", "") if isinstance(i, dict) else i.severity.value) == "blocker"
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

        # Record review round
        state["review_history"].append({
            "round": state["iteration"],
            "drama_critic_score": drama_score,
            "style_guard_score": style_score,
            "merged_score": merged_score,
            "verdict": verdict,
            "blocker_count": blocker_count,
            "issue_count": len(deduped),
        })

        return state

    # ── Node: Revise Draft ──

    async def revise_draft(state: ScriptReviewState) -> ScriptReviewState:
        """Writer revises the script based on merged feedback."""
        try:
            # Build ReviewFeedback from merged issues
            from app.agents.base import Issue, IssueSeverity, ReviewFeedback, Verdict

            drama = state.get("drama_critic_feedback", {}) or {}
            style = state.get("style_guard_feedback", {}) or {}

            all_issues_raw = drama.get("critical_issues", []) + style.get("critical_issues", [])
            issues = []
            for i in all_issues_raw:
                if isinstance(i, dict):
                    issues.append(Issue(
                        id=i.get("id", ""),
                        severity=IssueSeverity(i.get("severity", "minor")),
                        location=i.get("location", ""),
                        category=i.get("category", ""),
                        description=i.get("description", ""),
                        evidence=i.get("evidence", ""),
                        suggestion=i.get("suggestion", ""),
                    ))

            verdict_map = {
                "approved": Verdict.APPROVED,
                "approved_with_minor": Verdict.APPROVED_WITH_MINOR,
                "needs_revision": Verdict.NEEDS_REVISION,
                "escalated": Verdict.REJECTED,
            }
            verdict = verdict_map.get(state["merged_verdict"], Verdict.NEEDS_REVISION)

            feedback = ReviewFeedback(
                overall_verdict=verdict,
                total_score=state["merged_score"],
                dimension_scores={},
                critical_issues=issues,
            )

            revised = await writer.revise(feedback, state["script"])
            state["script"] = revised
            state["iteration"] += 1

        except Exception as e:
            state["error"] = f"Revision failed: {e}"
            state["merged_verdict"] = "escalated"

        return state

    # ── Node: Escalate to Human ──

    async def escalate_to_human(state: ScriptReviewState) -> ScriptReviewState:
        """Escalate to human for decision."""
        state["merged_verdict"] = "escalated"
        return state

    # ── Routing ──

    def decide_next(state: ScriptReviewState) -> str:
        """Route based on merged verdict."""
        verdict = state.get("merged_verdict", "escalated")
        if verdict in ("approved", "approved_with_minor"):
            return "complete"
        elif verdict == "needs_revision":
            return "revise"
        else:
            return "escalate"

    # ── Build Graph ──

    graph.add_node("generate", generate_draft)
    graph.add_node("review", parallel_review)
    graph.add_node("merge", merge_reviews)
    graph.add_node("revise", revise_draft)
    graph.add_node("escalate", escalate_to_human)

    graph.set_entry_point("generate")

    graph.add_edge("generate", "review")
    graph.add_edge("review", "merge")
    graph.add_conditional_edges("merge", decide_next, {
        "complete": END,
        "revise": "revise",
        "escalate": "escalate",
    })
    graph.add_edge("revise", "review")  # Loop back for re-review
    graph.add_edge("escalate", END)

    return graph


def create_stage1_graph(llm_service: Any = None):
    """Factory to create a compiled Stage 1 graph with LLM-powered agents.

    Args:
        llm_service: LLMService instance. If None, agents run in heuristic-only mode.
    """
    from app.agents.stage1_script.critic import DramaCriticAgent
    from app.agents.stage1_script.style_guard import StyleGuardAgent
    from app.agents.stage1_script.writer import ScriptWriterAgent

    writer = ScriptWriterAgent(llm_service=llm_service)
    critic = DramaCriticAgent(llm_service=llm_service)
    style_guard = StyleGuardAgent(llm_service=llm_service)

    graph = build_stage1_graph(
        writer=writer,
        critic=critic,
        style_guard=style_guard,
        llm_service=llm_service,
    )
    return graph.compile()
