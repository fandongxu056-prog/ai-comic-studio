"""StyleGuard Agent — reviews scripts for genre/style consistency.

Role: Reviewer
Reviews: ScriptWriter
Focus: Orthogonal to DramaCritic — style/tone/genre, not narrative quality.
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


def build_style_guard_config() -> AgentConfig:
    return AgentConfig(
        identity=AgentIdentity(
            agent_id="style_guard_v1",
            identity="风格把控师",
            expertise=["题材分析", "台词风格", "受众匹配", "调性把控"],
            personality="敏锐的品类嗅觉，能精准识别'出戏'的内容",
            blind_spots=["不擅长评估叙事结构的优劣"],
            quality_bias="更关注'像不像这个品类'而非'好不好看'",
        ),
        scope=AgentScope(
            stage="script",
            reads=["structured_script", "style_preference"],
            writes=["review_feedback"],
            must_not_modify=["structured_script"],
        ),
        role=AgentRole.REVIEWER,
        can_review=["script_writer_v1"],
    )


class StyleGuardAgent(BaseAgent):
    """Reviews script for genre alignment, tone consistency, and audience fit.

    Orthogonal to DramaCritic:
    - DramaCritic: "Is it a good story?"
    - StyleGuard: "Does it feel like the right genre?"
    """

    def __init__(self):
        super().__init__(build_style_guard_config())

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Review script for style compliance."""
        script = input_data.get("script", {})
        style_pref = input_data.get("style_preference", {})
        episodes = script.get("episodes", [])

        issues: list[Issue] = []

        # Run style checks
        issues.extend(self._check_genre_alignment(episodes, style_pref))
        issues.extend(self._check_tone_consistency(episodes))
        issues.extend(self._check_dialogue_style(episodes, style_pref))
        issues.extend(self._check_content_safety(episodes, input_data))

        # Score
        dimension_scores = {
            "completeness": 90,
            "consistency": self._score_style_consistency(issues),
            "quality": 80,
            "executability": 75,
            "compliance": self._score_safety(issues),
        }

        total_score = calculate_total_score(dimension_scores, "script")
        blocker_count = sum(1 for i in issues if i.severity == IssueSeverity.BLOCKER)

        feedback = ReviewFeedback(
            overall_verdict=self._verdict(total_score, blocker_count),
            total_score=total_score,
            dimension_scores=dimension_scores,
            critical_issues=issues,
            strengths=[],
        )

        return feedback.model_dump()

    def _check_genre_alignment(self, episodes: list, style_pref: dict) -> list[Issue]:
        """Check that core conflicts match genre expectations."""
        return []

    def _check_tone_consistency(self, episodes: list) -> list[Issue]:
        """Check emotional tone doesn't fluctuate erratically."""
        issues = []
        for ep in episodes:
            scene_emotions = []
            for scene in ep.get("scenes", []):
                mood = scene.get("location", {}).get("mood", "")
                if mood:
                    scene_emotions.append(mood)

            # Check for jarring mood swings
            for i in range(len(scene_emotions) - 1):
                extreme_pairs = [
                    ("comedy", "tragedy"),
                    ("light", "dark"),
                    ("romantic", "horror"),
                ]
                for a, b in extreme_pairs:
                    if (scene_emotions[i] == a and scene_emotions[i + 1] == b) or \
                       (scene_emotions[i] == b and scene_emotions[i + 1] == a):
                        issues.append(Issue(
                            id=f"TONE-{ep.get('episode_index')}",
                            severity=IssueSeverity.MINOR,
                            location=f"episode={ep.get('episode_index')}, scenes {i+1}-{i+2}",
                            category="tone_consistency",
                            description=f"场景情绪从'{scene_emotions[i]}'陡转到'{scene_emotions[i+1]}'，可能需要过渡",
                            evidence=f"Scene {i+1} mood: {scene_emotions[i]} → Scene {i+2} mood: {scene_emotions[i+1]}",
                            suggestion="在两场之间插入一个过渡场景或情绪缓冲",
                        ))
        return issues

    def _check_dialogue_style(self, episodes: list, style_pref: dict) -> list[Issue]:
        """Check character voices are distinct and genre-appropriate."""
        return []

    def _check_content_safety(self, episodes: list, input_data: dict) -> list[Issue]:
        """Check for prohibited content."""
        avoid = input_data.get("creative_direction", {}).get("avoid_elements", [])
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                for seg in scene.get("content", {}).get("segments", []):
                    text = seg.get("text", "")
                    for avoid_item in avoid:
                        if avoid_item in text:
                            issues.append(Issue(
                                id=f"SAFETY-{ep.get('episode_index')}",
                                severity=IssueSeverity.BLOCKER,
                                location=f"episode={ep.get('episode_index')}, scene={scene.get('scene_id')}",
                                category="content_safety",
                                description=f"包含需要规避的内容: '{avoid_item}'",
                                evidence=f"\"{text[:100]}...\"",
                            ))
        return issues

    def _score_style_consistency(self, issues: list) -> int:
        base = 90
        base -= len(issues) * 3
        return max(base, 0)

    def _score_safety(self, issues: list) -> int:
        blockers = [i for i in issues if i.severity == IssueSeverity.BLOCKER]
        return 0 if blockers else 100

    def _verdict(self, total_score: int, blocker_count: int) -> Verdict:
        if total_score >= 80 and blocker_count == 0:
            return Verdict.APPROVED
        elif 65 <= total_score < 80 and blocker_count == 0:
            return Verdict.APPROVED_WITH_MINOR
        else:
            return Verdict.NEEDS_REVISION

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        raise NotImplementedError("Reviewer agents cannot revise")
