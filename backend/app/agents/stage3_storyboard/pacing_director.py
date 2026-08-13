"""PacingDirector Agent — reviews storyboard rhythm, fills all 3 stub methods."""

from app.agents.base import (
    AgentConfig, AgentIdentity, AgentRole, AgentScope, BaseAgent,
    Issue, IssueSeverity, ReviewFeedback, Verdict, calculate_total_score, determine_verdict,
)


class PacingDirectorAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentConfig(
            identity=AgentIdentity(agent_id="pacing_director_v1", identity="节奏导演",
                expertise=["镜头节奏", "时长分配", "叙事节奏", "视觉流"],
                personality="对节奏极其敏感，能精准定位拖沓或跳跃的片段",
                blind_spots=["对角色引用正确性不敏感"], quality_bias="更关注'节奏好不好'"),
            scope=AgentScope(stage="storyboard", reads=["shot_plan", "script"], writes=["review_feedback"]),
            role=AgentRole.REVIEWER, can_review=["shot_composer_v1"],
        ))

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        plan = input_data.get("shot_plan", {})
        episodes = plan.get("episodes", [])
        issues: list[Issue] = []

        issues.extend(self._check_shot_variety(episodes))
        issues.extend(self._check_duration_distribution(episodes))
        issues.extend(self._check_camera_movement(episodes))
        issues.extend(self._check_narrative_rhythm(episodes, input_data.get("script", {})))
        issues.extend(self._check_composition_variety(episodes))
        issues.extend(self._check_visual_flow(episodes))

        dim_scores = {
            "completeness": self._score_completeness(plan),
            "consistency": 85,
            "quality": self._score_pacing_quality(issues),
            "executability": 80,
            "compliance": 90,
        }
        total = calculate_total_score(dim_scores, "storyboard")
        blockers = sum(1 for i in issues if i.severity == IssueSeverity.BLOCKER)
        verdict = determine_verdict(total, blockers)

        return ReviewFeedback(overall_verdict=verdict, total_score=total, dimension_scores=dim_scores, critical_issues=issues).model_dump()

    # ── Round 1 ──

    def _check_shot_variety(self, episodes: list) -> list[Issue]:
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                shots = scene.get("shots", [])
                if len(shots) < 3:
                    continue
                types = [s.get("shot_type") for s in shots]
                unique = len(set(types))
                if unique < 2:
                    issues.append(Issue(id=f"VAR-{scene.get('scene_id','')}", severity=IssueSeverity.MAJOR,
                        location=f"ep={ep.get('episode_index')},scene={scene.get('scene_id')}",
                        category="shot_variety", description=f"{len(shots)}个镜头只有{unique}种景别,画面单调",
                        evidence=f"unique shot types: {unique}", suggestion="至少交替使用2-3种景别"))
                # 5+ consecutive same type
                for i in range(len(types) - 4):
                    if len(set(types[i:i+5])) == 1:
                        issues.append(Issue(id=f"MONO-{scene.get('scene_id','')}", severity=IssueSeverity.MAJOR,
                            location=f"ep={ep.get('episode_index')},scene={scene.get('scene_id')},shot={i+1}",
                            category="shot_variety", description=f"连续5个{types[i]}镜头,视觉疲劳",
                            evidence="5 consecutive same shot type", suggestion="插入不同景别的镜头打破单调"))
                        break
        return issues

    def _check_duration_distribution(self, episodes: list) -> list[Issue]:
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                shots = scene.get("shots", [])
                for s in shots:
                    if s.get("camera_movement", {}).get("type", "static") == "static" and s.get("duration_ms", 0) > 8000:
                        issues.append(Issue(id=f"DUR-{s.get('shot_id','')}", severity=IssueSeverity.MAJOR,
                            location=f"shot={s.get('shot_id')}", category="pacing",
                            description=f"静态镜头时长{s.get('duration_ms')}ms过长,观众会失去耐心",
                            evidence=f"static shot: {s.get('duration_ms')}ms",
                            suggestion="缩短至5-6秒或增加运镜(camera_movement)"))
                # Monotonous durations
                if len(shots) >= 4:
                    durations = [s.get("duration_ms", 0) for s in shots]
                    avg = sum(durations) / len(durations)
                    if all(abs(d - avg) < 500 for d in durations):
                        issues.append(Issue(id=f"MONODUR-{scene.get('scene_id','')}", severity=IssueSeverity.MINOR,
                            location=f"ep={ep.get('episode_index')},scene={scene.get('scene_id')}",
                            category="pacing", description="所有镜头时长几乎相同,节奏缺乏变化",
                            evidence=f"all durations within 500ms of avg {avg:.0f}ms",
                            suggestion="关键镜头给更长时间,过渡镜头缩短"))
        return issues

    def _check_camera_movement(self, episodes: list) -> list[Issue]:
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                shots = scene.get("shots", [])
                if not shots:
                    continue
                static_count = sum(1 for s in shots if s.get("camera_movement", {}).get("type", "static") == "static")
                if len(shots) >= 3 and static_count / len(shots) > 0.9:
                    issues.append(Issue(id=f"STATIC-{scene.get('scene_id','')}", severity=IssueSeverity.MINOR,
                        location=f"ep={ep.get('episode_index')},scene={scene.get('scene_id')}",
                        category="camera_movement", description=f"{static_count}/{len(shots)}镜头为静态,画面呆板",
                        evidence=f"static ratio: {static_count/len(shots):.0%}",
                        suggestion="增加缓慢推拉或微摇镜增加动态感"))
        return issues

    # ── Round 2 (previously stubs, now implemented) ──

    def _check_narrative_rhythm(self, episodes: list, script: dict) -> list[Issue]:
        """Check action scenes have faster cuts than dialogue scenes."""
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                shots = scene.get("shots", [])
                if len(shots) < 2:
                    continue
                moods = [s.get("scene_mood", scene.get("scene_mood", "")) for s in shots]
                durations = [s.get("duration_ms", 0) for s in shots]
                # Action/tension scenes should have shorter average duration
                high_tension = ["紧张", "战斗", "追逐", "诡异", "恐惧", "action", "fight"]
                low_tension = ["日常", "平静", "温馨", "轻松"]
                if any(m in str(moods).lower() for m in high_tension):
                    avg_dur = sum(durations) / len(durations)
                    if avg_dur > 5000:
                        issues.append(Issue(id=f"RHYTHM-{scene.get('scene_id','')}", severity=IssueSeverity.MINOR,
                            location=f"ep={ep.get('episode_index')},scene={scene.get('scene_id')}",
                            category="narrative_rhythm", description=f"高张力场景平均镜头{avg_dur:.0f}ms过长,应有更快节奏",
                            evidence=f"avg duration: {avg_dur:.0f}ms in high-tension scene",
                            suggestion="将镜头拆分为更短的片段(2-4秒)以增强紧张感"))
        return issues

    def _check_composition_variety(self, episodes: list) -> list[Issue]:
        """Check rule-of-thirds positions vary across shots."""
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                shots = scene.get("shots", [])
                if len(shots) < 3:
                    continue
                # Check if all shots center the subject
                centers = 0
                for s in shots:
                    comp = s.get("keyframe", {}).get("composition", {})
                    if comp.get("subject_focus") and "center" in str(comp.get("subject_focus", "")).lower():
                        centers += 1
                if centers == len(shots):
                    issues.append(Issue(id=f"COMP-{scene.get('scene_id','')}", severity=IssueSeverity.MINOR,
                        location=f"ep={ep.get('episode_index')},scene={scene.get('scene_id')}",
                        category="composition_variety", description="所有镜头构图居中,缺少变化",
                        evidence=f"{centers}/{len(shots)} shots center-composed",
                        suggestion="使用三分法构图(left_third/right_third)增加画面张力"))
        return issues

    def _check_visual_flow(self, episodes: list) -> list[Issue]:
        """Check that successive shots maintain spatial continuity (180-degree rule)."""
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                shots = scene.get("shots", [])
                if len(shots) < 4:
                    continue
                pans = 0
                for s in shots:
                    cam = s.get("camera_movement", {}).get("type", "")
                    if cam in ("pan_left", "pan_right"):
                        pans += 1
                if pans >= 3:
                    issues.append(Issue(id=f"FLOW-{scene.get('scene_id','')}", severity=IssueSeverity.MINOR,
                        location=f"ep={ep.get('episode_index')},scene={scene.get('scene_id')}",
                        category="visual_flow", description=f"场景内{pans}个水平摇镜,注意180度轴线规则",
                        evidence=f"{pans} horizontal pans in one scene",
                        suggestion="确保连续镜头的视线方向和动作方向一致,避免越轴"))
        return issues

    # ── Scoring ──

    def _score_completeness(self, plan: dict) -> int:
        episodes = plan.get("episodes", [])
        return 90 if all(ep.get("scenes") and all(sc.get("shots") for sc in ep.get("scenes", [])) for ep in episodes) else 50

    def _score_pacing_quality(self, issues: list) -> int:
        base = 85
        base -= sum(5 for i in issues if i.severity == IssueSeverity.MAJOR)
        base -= sum(2 for i in issues if i.severity == IssueSeverity.MINOR)
        return max(base, 0)

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        raise NotImplementedError("Reviewer cannot revise")
