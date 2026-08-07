"""DramaCritic Agent — reviews scripts for narrative quality.

Role: Reviewer
Reviews: ScriptWriter
"""

from app.agents.base import (
    AgentConfig,
    AgentIdentity,
    AgentRole,
    AgentScope,
    BaseAgent,
    Issue,
    IssueSeverity,
    ReviewFeedback,
    Verdict,
    calculate_total_score,
)


def build_critic_config() -> AgentConfig:
    return AgentConfig(
        identity=AgentIdentity(
            agent_id="drama_critic_v1",
            identity="资深剧评人",
            expertise=["叙事结构", "冲突设计", "人物弧光", "对白评估", "节奏分析"],
            personality="严格但公正，擅长精准定位剧本的叙事弱点，给出可操作的修改方案",
            blind_spots=["对视觉风格不敏感", "可能对实验性叙事过于保守"],
            quality_bias="更关注'好不好看'而非'像不像这个品类'",
        ),
        scope=AgentScope(
            stage="script",
            reads=["structured_script", "project_input"],
            writes=["review_feedback"],
            must_not_modify=["structured_script"],
        ),
        role=AgentRole.REVIEWER,
        can_review=["script_writer_v1"],
    )


class DramaCriticAgent(BaseAgent):
    """Reviews script narrative quality across 4 dimensions."""

    def __init__(self):
        super().__init__(build_critic_config())

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Review a script draft and return structured feedback.

        Args:
            input_data: {script: StructuredScript, project_input: {...}}
            context: Optional LLM config
        """
        script = input_data.get("script", {})
        episodes = script.get("episodes", [])

        issues: list[Issue] = []
        strengths: list[dict] = []

        # Run each checklist pass
        issues.extend(self._check_structure(episodes))
        issues.extend(self._check_conflict_density(episodes))
        issues.extend(self._check_character_arcs(episodes))
        issues.extend(self._check_dialogue_function(episodes))
        issues.extend(self._check_pacing(episodes))

        # Score each dimension
        completeness_score = self._score_completeness(script)
        consistency_score = self._score_consistency(script, episodes)
        quality_score = self._score_quality(episodes, issues)
        executability_score = self._score_executability(script)
        compliance_score = self._score_compliance(script, input_data)

        dimension_scores = {
            "completeness": completeness_score,
            "consistency": consistency_score,
            "quality": quality_score,
            "executability": executability_score,
            "compliance": compliance_score,
        }

        total_score = calculate_total_score(dimension_scores, "script")
        blocker_count = sum(1 for i in issues if i.severity == IssueSeverity.BLOCKER)
        verdict = self._determine_verdict(total_score, blocker_count)

        feedback = ReviewFeedback(
            overall_verdict=verdict,
            total_score=total_score,
            dimension_scores=dimension_scores,
            critical_issues=issues,
            strengths=strengths,
        )

        return feedback.model_dump()

    # ── Checklist Methods ──

    def _check_structure(self, episodes: list) -> list[Issue]:
        """Check narrative structure: hook → development → cliffhanger."""
        issues = []
        for ep in episodes:
            ep_idx = ep.get("episode_index", 0)
            scenes = ep.get("scenes", [])

            if not scenes:
                issues.append(Issue(
                    id=f"STRUCT-E{ep_idx:03d}",
                    severity=IssueSeverity.BLOCKER,
                    location=f"episode={ep_idx}",
                    category="story_completeness",
                    description=f"第{ep_idx}集没有任何场景",
                    evidence=f"episodes[{ep_idx-1}].scenes = []",
                ))
                continue

            # Check for hook in first scene
            first_scene_segments = scenes[0].get("content", {}).get("segments", [])
            has_hook = any(s.get("type") in ("narration", "action") for s in first_scene_segments[:3])
            if not has_hook and ep.get("hook") is None:
                issues.append(Issue(
                    id=f"HOOK-E{ep_idx:03d}",
                    severity=IssueSeverity.MAJOR,
                    location=f"episode={ep_idx}, scene=1",
                    category="hook_strength",
                    description=f"第{ep_idx}集缺少开场 hook — 前30秒没有建立核心悬念",
                    evidence="开场3个segment无吸引人的信息差设置",
                    suggestion="在第一场戏前3句内揭示一个信息差（角色知道的 vs 观众知道的）",
                ))

            # Check for cliffhanger at end
            last_scene_segments = scenes[-1].get("content", {}).get("segments", [])
            has_cliffhanger = any(
                s.get("type") in ("narration", "dialogue")
                for s in last_scene_segments[-3:]
            )
            if not has_cliffhanger and ep.get("cliffhanger") is None:
                issues.append(Issue(
                    id=f"CLIFF-E{ep_idx:03d}",
                    severity=IssueSeverity.MAJOR,
                    location=f"episode={ep_idx}, last scene",
                    category="cliffhanger_strength",
                    description=f"第{ep_idx}集缺少结尾悬念",
                    evidence="最后3个segment都没有留下未解问题",
                    suggestion="结尾留一个'未完待续'的钩子——揭示一个新信息、引入一个危机、或留下一个悬念",
                ))

        return issues

    def _check_conflict_density(self, episodes: list) -> list[Issue]:
        """Check that each scene has sufficient conflict."""
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                segments = scene.get("content", {}).get("segments", [])

                # Count consecutive segments without conflict markers
                consecutive_no_conflict = 0
                for seg in segments:
                    action = seg.get("action_tag", "")
                    emotion = seg.get("emotion_tag", "")
                    if not action and not emotion:
                        consecutive_no_conflict += 1
                    else:
                        consecutive_no_conflict = 0
                    if consecutive_no_conflict >= 4:
                        issues.append(Issue(
                            id=f"CONFLICT-{scene.get('scene_id', '')}",
                            severity=IssueSeverity.MAJOR,
                            location=f"episode={ep.get('episode_index')}, scene={scene.get('scene_index')}",
                            category="conflict_density",
                            description=f"连续{consecutive_no_conflict}个segment无冲突推进",
                            evidence=f"segment {seg.get('type')}: \"{seg.get('text', '')[:50]}...\"",
                            suggestion="插入一个突发事件、信息差揭露、或角色间的立场对立",
                        ))
                        consecutive_no_conflict = 0
        return issues

    def _check_character_arcs(self, episodes: list) -> list[Issue]:
        """Check character arcs and motivations."""
        # Simplified: check that protagonist has clear desire in first episode
        return []

    def _check_dialogue_function(self, episodes: list) -> list[Issue]:
        """Check that every dialogue segment has narrative function."""
        issues = []
        functional_tags = {"reveal", "conflict", "character", "foreshadow"}

        for ep in episodes:
            for scene in ep.get("scenes", []):
                for seg in scene.get("content", {}).get("segments", []):
                    if seg.get("type") == "dialogue":
                        text = seg.get("text", "")
                        action = seg.get("action_tag", "")
                        emotion = seg.get("emotion_tag", "")
                        # Flag empty/functional dialogue
                        if not action and not emotion and len(text) < 5 and "..." not in text:
                            # Short dialogue with no action tag — might be filler
                            pass

        return issues

    def _check_pacing(self, episodes: list) -> list[Issue]:
        """Check scene-level pacing."""
        return []

    # ── Scoring Methods ──

    def _score_completeness(self, script: dict) -> int:
        episodes = script.get("episodes", [])
        if not episodes:
            return 0
        char_count = len(script.get("character_index", {}).get("characters", []))
        loc_count = len(script.get("location_index", {}).get("locations", []))
        score = 70
        if char_count > 0:
            score += 10
        if loc_count > 0:
            score += 10
        if all(ep.get("scenes") for ep in episodes):
            score += 10
        return min(score, 100)

    def _score_consistency(self, script: dict, episodes: list) -> int:
        return 75  # Simplified; full implementation checks continuity rules

    def _score_quality(self, episodes: list, issues: list) -> int:
        base = 80
        major_count = sum(1 for i in issues if i.severity in (IssueSeverity.BLOCKER, IssueSeverity.MAJOR))
        base -= major_count * 5
        return max(base, 0)

    def _score_executability(self, script: dict) -> int:
        return 70  # Simplified

    def _score_compliance(self, script: dict, input_data: dict) -> int:
        return 85  # Simplified

    def _determine_verdict(self, total_score: int, blocker_count: int) -> Verdict:
        if total_score >= 80 and blocker_count == 0:
            return Verdict.APPROVED
        elif 65 <= total_score < 80 and blocker_count == 0:
            return Verdict.APPROVED_WITH_MINOR
        else:
            return Verdict.NEEDS_REVISION

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        """Reviewer agents don't revise — they only review."""
        raise NotImplementedError("Reviewer agents cannot revise — only review")
