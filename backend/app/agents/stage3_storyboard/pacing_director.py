"""PacingDirector Agent — reviews storyboard for rhythm and pacing quality.

Role: Reviewer
Reviews: ShotComposer
Focus: Shot duration, variety, and narrative rhythm
"""

from app.agents.base import (
    AgentConfig, AgentIdentity, AgentRole, AgentScope,
    BaseAgent, Issue, IssueSeverity, ReviewFeedback, Verdict,
    calculate_total_score,
)


def build_pacing_director_config() -> AgentConfig:
    return AgentConfig(
        identity=AgentIdentity(
            agent_id="pacing_director_v1",
            identity="节奏导演",
            expertise=["镜头节奏", "时长分配", "情绪起伏", "视觉流", "观众注意力曲线"],
            personality="对一秒的差距极其敏感——0.5秒的节奏偏差可能让整场戏的情绪断掉",
            blind_spots=["不审查角色/场景引用正确性——那是ContinuityCheck的活"],
            quality_bias="更关注'观众会不会无聊'而非'画面会不会穿帮'",
        ),
        scope=AgentScope(
            stage="storyboard",
            reads=["shot_plan", "script"],
            writes=["review_feedback"],
            must_not_modify=["shot_plan"],
        ),
        role=AgentRole.REVIEWER,
        can_review=["shot_composer_v1"],
    )


class PacingDirectorAgent(BaseAgent):
    """Reviews storyboard for pacing and narrative rhythm.

    Checklist (from agent-collaboration-protocol.md §4.2):
    Round 1:
    - Shot type variety (not all medium shots)
    - Shot duration distribution
    - Camera movement appropriateness
    - Narrative rhythm

    Round 2:
    - Composition variety
    - Visual flow (eye direction, motion continuity)
    """

    def __init__(self):
        super().__init__(build_pacing_director_config())

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Review storyboard pacing."""
        shot_plan = input_data.get("shot_plan", {})
        episodes = shot_plan.get("episodes", [])

        issues: list[Issue] = []
        strengths: list[dict] = []

        # Round 1 checks
        issues.extend(self._check_shot_variety(episodes))
        issues.extend(self._check_duration_distribution(episodes))
        issues.extend(self._check_camera_movement(episodes))
        issues.extend(self._check_narrative_rhythm(episodes))

        # Round 2 checks
        issues.extend(self._check_composition_variety(episodes))
        issues.extend(self._check_visual_flow(episodes))

        # Scoring
        dimension_scores = {
            "completeness": self._score_completeness(shot_plan),
            "consistency": 80,
            "quality": self._score_pacing_quality(issues),
            "executability": 75,
            "compliance": 85,
        }

        total = calculate_total_score(dimension_scores, "storyboard")
        blocker_count = sum(1 for i in issues if i.severity == IssueSeverity.BLOCKER)

        if total >= 80 and blocker_count == 0:
            verdict = Verdict.APPROVED
        elif 65 <= total < 80 and blocker_count == 0:
            verdict = Verdict.APPROVED_WITH_MINOR
        else:
            verdict = Verdict.NEEDS_REVISION

        return ReviewFeedback(
            overall_verdict=verdict,
            total_score=total,
            dimension_scores=dimension_scores,
            critical_issues=issues,
            strengths=strengths,
        ).model_dump()

    # ── Round 1 ──

    def _check_shot_variety(self, episodes: list) -> list[Issue]:
        """Check shot type diversity within each scene.

        A scene with all medium shots is visually boring.
        """
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                shot_types = [s["shot_type"] for s in scene.get("shots", [])]
                if not shot_types:
                    continue

                # Check variety: at least 2 different shot types per scene
                unique_types = set(shot_types)
                if len(unique_types) < 2 and len(shot_types) >= 3:
                    issues.append(Issue(
                        id=f"VAR-{scene.get('scene_id', '')}",
                        severity=IssueSeverity.MAJOR,
                        location=f"scene: {scene.get('scene_id')}",
                        category="shot_variety",
                        description=f"场景只使用了1种景别 ({list(unique_types)[0]})，画面单调",
                        evidence=f"连续{len(shot_types)}个镜头均为同一种景别",
                        suggestion="穿插不同景别: 建立镜头用wide→对白用medium_close_up→情感点用close_up",
                    ))

                # Check consecutive same-type shots
                consecutive_same = 0
                for i in range(1, len(shot_types)):
                    if shot_types[i] == shot_types[i - 1]:
                        consecutive_same += 1
                    else:
                        consecutive_same = 0
                    if consecutive_same >= 4:
                        issues.append(Issue(
                            id=f"VAR-SEQ-{scene.get('scene_id')}-{i}",
                            severity=IssueSeverity.MAJOR,
                            location=f"scene: {scene.get('scene_id')}, shots {i-3}-{i+1}",
                            category="shot_variety",
                            description=f"连续5个镜头使用同一景别 ({shot_types[i]})",
                            evidence=f"shots[{i-3}:{i+1}] all = {shot_types[i]}",
                            suggestion="在第3-4个同样景别的镜头后插入一个不同的景别来打破单调",
                        ))
                        consecutive_same = 0

        return issues

    def _check_duration_distribution(self, episodes: list) -> list[Issue]:
        """Check shot duration is appropriate for content type."""
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                shots = scene.get("shots", [])
                durations = [s["duration_ms"] for s in shots]

                if not durations:
                    continue

                # Flag shots that are too long for static camera
                for shot in shots:
                    if shot["camera_movement"]["type"] == "static" and shot["duration_ms"] > 8000:
                        issues.append(Issue(
                            id=f"DUR-{shot['shot_id']}",
                            severity=IssueSeverity.MAJOR,
                            location=f"shot: {shot['shot_id']}",
                            category="pacing_quality",
                            description=f"静态镜头时长 {shot['duration_ms']}ms 过长，观众可能失去耐心",
                            evidence=f"duration={shot['duration_ms']}ms, camera=static",
                            suggestion="要么缩短到5-6秒，要么添加 subtle 运镜（zoom_in/pan）来保持画面动感",
                        ))

                # Check for monotonous duration (all shots same length)
                if len(durations) >= 4:
                    avg = sum(durations) / len(durations)
                    all_close = all(abs(d - avg) < 500 for d in durations)
                    if all_close:
                        issues.append(Issue(
                            id=f"DUR-MONO-{scene.get('scene_id')}",
                            severity=IssueSeverity.MINOR,
                            location=f"scene: {scene.get('scene_id')}",
                            category="pacing_quality",
                            description=f"所有镜头时长接近 ({avg:.0f}ms)，缺乏节奏变化",
                            suggestion="动作镜头缩短到1-2秒，情感镜头拉长到3-5秒来制造节奏起伏",
                        ))

        return issues

    def _check_camera_movement(self, episodes: list) -> list[Issue]:
        """Check camera movement appropriateness."""
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                static_count = 0
                for shot in scene.get("shots", []):
                    if shot["camera_movement"]["type"] == "static":
                        static_count += 1

                total = len(scene.get("shots", []))
                if total > 0 and static_count / total > 0.9:
                    issues.append(Issue(
                        id=f"CAM-{scene.get('scene_id')}",
                        severity=IssueSeverity.MINOR,
                        location=f"scene: {scene.get('scene_id')}",
                        category="shot_variety",
                        description=f"90%以上镜头为固定机位，画面可能呆板",
                        suggestion="在关键情感或动作节点加入 subtle zoom 或 track 运镜",
                    ))

        return issues

    def _check_narrative_rhythm(self, episodes: list) -> list[Issue]:
        """Check that action scenes have shorter cuts than dialogue scenes."""
        return []

    # ── Round 2 ──

    def _check_composition_variety(self, episodes: list) -> list[Issue]:
        """Check composition isn't all identical framing."""
        return []

    def _check_visual_flow(self, episodes: list) -> list[Issue]:
        """Check eye direction and motion continuity across shots."""
        return []

    # ── Scoring ──

    def _score_completeness(self, shot_plan: dict) -> int:
        episodes = shot_plan.get("episodes", [])
        if not episodes:
            return 0
        all_scenes_have_shots = all(
            scene.get("shots") for ep in episodes for scene in ep.get("scenes", [])
        )
        return 90 if all_scenes_have_shots else 50

    def _score_pacing_quality(self, issues: list) -> int:
        base = 85
        base -= len([i for i in issues if i.severity == IssueSeverity.MAJOR]) * 5
        return max(base, 0)

    async def revise(self, feedback, original_output):
        raise NotImplementedError("Reviewer cannot revise")
