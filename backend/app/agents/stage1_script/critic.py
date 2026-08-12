"""DramaCritic Agent — reviews scripts for narrative quality.

Role: Reviewer
Reviews: ScriptWriter

Combines heuristic checks (fast, zero-cost) with optional LLM deep analysis.
"""

from typing import Any

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
    determine_verdict,
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
    """Reviews script narrative quality — heuristic + LLM hybrid."""

    def __init__(self, llm_service: Any = None):
        super().__init__(build_critic_config())
        self.llm_service = llm_service

    # ── Main Entry ──

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Review a script draft and return structured feedback.

        Args:
            input_data: {script: StructuredScript, project_input: {...}, style_preference: {...}}
            context: Optional {llm_service, ...}
        """
        script = input_data.get("script", {})
        episodes = script.get("episodes", [])
        llm = (context or {}).get("llm_service", self.llm_service)

        issues: list[Issue] = []
        strengths: list[dict] = []

        # 1. Heuristic checks (always run — fast, deterministic)
        issues.extend(self._check_structure(episodes))
        issues.extend(self._check_conflict_density(episodes))
        issues.extend(self._check_character_arcs(script, episodes))
        issues.extend(self._check_dialogue_function(episodes))
        issues.extend(self._check_pacing(episodes))

        # 2. LLM deep analysis (if available)
        if llm and episodes:
            try:
                llm_issues, llm_strengths = await self._llm_review(script, llm)
                issues = self._merge_issues(issues, llm_issues)
                strengths.extend(llm_strengths)
            except Exception:
                pass  # LLM failure → degrade gracefully to heuristic-only

        # 3. Score
        dimension_scores = {
            "completeness": self._score_completeness(script),
            "consistency": self._score_consistency(script, episodes),
            "quality": self._score_quality(episodes, issues),
            "executability": self._score_executability(script),
            "compliance": self._score_compliance(script, input_data),
        }

        total_score = calculate_total_score(dimension_scores, "script")
        blocker_count = sum(1 for i in issues if i.severity == IssueSeverity.BLOCKER)
        verdict = determine_verdict(total_score, blocker_count)

        feedback = ReviewFeedback(
            overall_verdict=verdict,
            total_score=total_score,
            dimension_scores=dimension_scores,
            critical_issues=issues,
            strengths=strengths,
        )

        return feedback.model_dump()

    # ── Heuristic Checklist Methods ──

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
                    evidence=f"episodes[{ep_idx - 1}].scenes = []",
                ))
                continue

            # Check for hook in first scene
            first_segs = scenes[0].get("content", {}).get("segments", [])
            has_hook = any(
                s.get("type") in ("narration", "action") and len(s.get("text", "")) > 10
                for s in first_segs[:3]
            )
            if not has_hook and not ep.get("hook"):
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
            last_segs = scenes[-1].get("content", {}).get("segments", [])
            has_cliffhanger = any(
                s.get("type") in ("narration", "dialogue")
                for s in (last_segs[-3:] if len(last_segs) >= 3 else last_segs)
            )
            if not has_cliffhanger and not ep.get("cliffhanger"):
                issues.append(Issue(
                    id=f"CLIFF-E{ep_idx:03d}",
                    severity=IssueSeverity.MAJOR,
                    location=f"episode={ep_idx}, last scene",
                    category="cliffhanger_strength",
                    description=f"第{ep_idx}集缺少结尾悬念",
                    evidence="最后3个segment都没有留下未解问题",
                    suggestion="结尾留一个'未完待续'的钩子——揭示一个新信息、引入一个危机、或留下一个悬念",
                ))

            # Check scene count is reasonable
            if len(scenes) > 15:
                issues.append(Issue(
                    id=f"DENSE-E{ep_idx:03d}",
                    severity=IssueSeverity.MINOR,
                    location=f"episode={ep_idx}",
                    category="pacing",
                    description=f"第{ep_idx}集有{len(scenes)}个场景，可能过于碎片化",
                    evidence=f"scene count = {len(scenes)}",
                    suggestion=f"考虑合并相邻的短场景，保持每集3-10个场景",
                ))

        return issues

    def _check_conflict_density(self, episodes: list) -> list[Issue]:
        """Check that each scene has sufficient conflict."""
        issues = []
        for ep in episodes:
            ep_idx = ep.get("episode_index", 0)
            for scene in ep.get("scenes", []):
                scene_id = scene.get("scene_id", "")
                segments = scene.get("content", {}).get("segments", [])

                consecutive_no_conflict = 0
                for seg in segments:
                    action = seg.get("action_tag", "")
                    emotion = seg.get("emotion_tag", "")
                    if not action and not emotion:
                        consecutive_no_conflict += 1
                    else:
                        consecutive_no_conflict = 0
                    if consecutive_no_conflict >= 4:
                        text_preview = seg.get("text", "")[:50]
                        issues.append(Issue(
                            id=f"CONFLICT-{scene_id}-{consecutive_no_conflict}",
                            severity=IssueSeverity.MAJOR,
                            location=f"episode={ep_idx}, scene={scene.get('scene_index')}",
                            category="conflict_density",
                            description=f"连续{consecutive_no_conflict}个segment无冲突推进，观众会流失",
                            evidence=f"\"{text_preview}...\"",
                            suggestion="插入一个突发事件、信息差揭露、或角色间的立场对立",
                        ))
                        consecutive_no_conflict = 0
        return issues

    def _check_character_arcs(self, script: dict, episodes: list) -> list[Issue]:
        """Check character arcs and motivations."""
        issues = []
        char_index = script.get("character_index", [])
        if not char_index:
            return issues

        # Check protagonist has clear presence
        protagonists = [c for c in char_index if c.get("role_type") == "protagonist"]
        if not protagonists:
            issues.append(Issue(
                id="CHAR-NO-PROT",
                severity=IssueSeverity.BLOCKER,
                location="character_index",
                category="character_arcs",
                description="剧本没有明确的主角——角色索引中缺少 protagonist",
                evidence="character_index[].role_type != 'protagonist'",
                suggestion="指定一个角色为主角，确保其有明确的核心欲望和困境",
            ))

        for protag in protagonists:
            ref = protag.get("ref_name", "")
            if protag.get("scene_count", 0) < len(episodes):
                issues.append(Issue(
                    id=f"CHAR-ABSENT-{ref}",
                    severity=IssueSeverity.MAJOR,
                    location=f"character_index.{ref}",
                    category="character_arcs",
                    description=f"主角'{ref}'不是每集都出场（{protag.get('scene_count')}场景/{len(episodes)}集）",
                    evidence=f"scene_count={protag.get('scene_count')} < episode_count={len(episodes)}",
                    suggestion="确保主角在每一集中都有存在感",
                ))

        return issues

    def _check_dialogue_function(self, episodes: list) -> list[Issue]:
        """Check that dialogue segments serve narrative functions."""
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                dialogue_segs = [
                    s for s in scene.get("content", {}).get("segments", [])
                    if s.get("type") == "dialogue"
                ]
                # Flag scenes with excessive dialogue and no action breaks
                if len(dialogue_segs) > 12:
                    action_breaks = sum(
                        1 for s in scene.get("content", {}).get("segments", [])
                        if s.get("type") == "action"
                    )
                    if action_breaks < 2:
                        issues.append(Issue(
                            id=f"DIALOG-{scene.get('scene_id', '')}",
                            severity=IssueSeverity.MINOR,
                            location=f"episode={ep.get('episode_index')}, scene={scene.get('scene_index')}",
                            category="dialogue_naturalness",
                            description=f"场景有{len(dialogue_segs)}句连续对白，缺少动作穿插——'纯说话'场景观众会疲劳",
                            evidence=f"dialogue segments: {len(dialogue_segs)}, action breaks: {action_breaks}",
                            suggestion="在对白之间插入角色动作（action segment）或场景切换",
                        ))

                # Flag dialogue without character_ref
                for seg in dialogue_segs:
                    if not seg.get("character_ref"):
                        issues.append(Issue(
                            id=f"DIALOG-NOREF-{scene.get('scene_id', '')}",
                            severity=IssueSeverity.MAJOR,
                            location=f"episode={ep.get('episode_index')}, scene={scene.get('scene_index')}",
                            category="dialogue_naturalness",
                            description="对白缺少说话人标注（character_ref）",
                            evidence=f"\"{seg.get('text', '')[:50]}...\"",
                            suggestion="为每句对白指定 character_ref",
                        ))

        return issues

    def _check_pacing(self, episodes: list) -> list[Issue]:
        """Check scene-level and segment-level pacing."""
        issues = []
        for ep in episodes:
            scene_seg_counts = [
                len(scene.get("content", {}).get("segments", []))
                for scene in ep.get("scenes", [])
            ]
            if not scene_seg_counts:
                continue

            # Flag uneven scene distribution
            avg = sum(scene_seg_counts) / len(scene_seg_counts)
            for i, count in enumerate(scene_seg_counts):
                if count > avg * 3:
                    issues.append(Issue(
                        id=f"PACE-{ep.get('episode_index')}-S{i+1}",
                        severity=IssueSeverity.MINOR,
                        location=f"episode={ep.get('episode_index')}, scene={i+1}",
                        category="pacing",
                        description=f"场景{i+1}有{count}个segment，远超平均值{avg:.0f}，可能导致节奏失衡",
                        evidence=f"segment count {count} vs avg {avg:.0f}",
                        suggestion="拆分过长场景或精简不必要的对话",
                    ))

            # Episodes with too few or too many scenes
            ep_idx = ep.get("episode_index", 0)
            if len(ep.get("scenes", [])) < 2:
                issues.append(Issue(
                    id=f"PACE-TOOFEW-E{ep_idx:03d}",
                    severity=IssueSeverity.MAJOR,
                    location=f"episode={ep_idx}",
                    category="pacing",
                    description=f"第{ep_idx}集只有{len(ep.get('scenes', []))}个场景，节奏可能过于单调",
                    evidence=f"scene count = {len(ep.get('scenes', []))}",
                    suggestion="至少包含3个场景：建立→冲突→悬念",
                ))

        return issues

    # ── LLM Deep Review ──

    async def _llm_review(self, script: dict, llm_service: Any) -> tuple[list[Issue], list[dict]]:
        """Use LLM for deep narrative analysis."""
        import json

        # Serialize script summary for the LLM
        script_summary = self._serialize_for_review(script)

        system_prompt = """你是一位资深漫剧评人，擅长从叙事角度分析剧本质量。

请审查以下剧本，从以下维度找出问题:

1. **叙事结构**:
   - 每集是否有有效的 hook 和 cliffhanger？
   - 场景之间的因果关系是否清晰？
   - 是否有"流水账"式的叙事？

2. **冲突密度**:
   - 每个场景是否有至少1个冲突点？
   - 冲突是否逐步升级而非平铺直叙？
   - 是否有为了"凑时长"的无效对白？

3. **人物弧光**:
   - 主角是否有清晰的目标/欲望？
   - 配角是否有独立于主角的存在价值？
   - 角色情绪变化是否有铺垫（不突兀）？

4. **视觉潜力**:
   - 每个场景是否提供了足够的视觉想象空间？
   - 是否存在"纯对话场景"过于依赖语言而忽略画面？
   - 动作标注(action_tag)和情绪标签(emotion_tag)是否充分？

对于每个发现的问题，给出:
- severity: blocker | major | minor | suggestion
- location: 精确到 episode/scene/segment
- description: 清晰的问题描述
- evidence: 剧本中的具体证据（引用原文）
- suggestion: 可操作的修改建议

同时给出 2-3 个剧本的亮点（strengths）。

输出格式: 严格的 JSON"""

        human_prompt = f"""请审查以下剧本摘要:

---
{json.dumps(script_summary, ensure_ascii=False, indent=2)}
---

请输出 JSON 格式的审查结果:
{{
  "issues": [
    {{
      "severity": "major",
      "location": "episode=1, scene=2",
      "category": "conflict_density",
      "description": "连续4段对白无冲突推进",
      "evidence": "原文引用...",
      "suggestion": "插入一个突发事件..."
    }}
  ],
  "strengths": [
    {{"location": "episode=1, scene=1", "aspect": "开场悬念设置出色"}}
  ]
}}"""

        try:
            raw = await llm_service.generate_text(system_prompt, human_prompt, temperature=0.3)
            data = json.loads(self._extract_json(raw))

            issues = []
            for item in data.get("issues", []):
                sev = item.get("severity", "minor")
                try:
                    severity = IssueSeverity(sev)
                except ValueError:
                    severity = IssueSeverity.MINOR

                issues.append(Issue(
                    id=f"LLM-{item.get('category', 'review')}-{len(issues)+1}",
                    severity=severity,
                    location=item.get("location", ""),
                    category=item.get("category", "general"),
                    description=item.get("description", ""),
                    evidence=item.get("evidence", ""),
                    suggestion=item.get("suggestion", ""),
                ))

            strengths = data.get("strengths", [])
            return issues, strengths

        except Exception:
            return [], []

    # ── Scoring Methods ──

    def _score_completeness(self, script: dict) -> int:
        episodes = script.get("episodes", [])
        if not episodes:
            return 0
        score = 70
        char_count = len(script.get("character_index", []))
        loc_count = len(script.get("location_index", []))
        if char_count > 0:
            score += 10
        if loc_count > 0:
            score += 10
        if all(ep.get("scenes") for ep in episodes):
            score += 10
        return min(score, 100)

    def _score_consistency(self, script: dict, episodes: list) -> int:
        score = 75
        # Deduct for common consistency issues
        char_refs = set()
        for ep in episodes:
            for scene in ep.get("scenes", []):
                for cp in scene.get("characters_present", []):
                    char_refs.add(cp.get("character_ref"))
        index_refs = {c.get("ref_name") for c in script.get("character_index", [])}
        if index_refs:
            missing = char_refs - index_refs
            score -= len(missing) * 3
        return max(score, 0)

    def _score_quality(self, episodes: list, issues: list) -> int:
        base = 80
        major_count = sum(
            1 for i in issues
            if hasattr(i, 'severity') and i.severity in (IssueSeverity.BLOCKER, IssueSeverity.MAJOR)
        )
        base -= major_count * 5
        return max(base, 0)

    def _score_executability(self, script: dict) -> int:
        episodes = script.get("episodes", [])
        if not episodes:
            return 0
        # Check visual potential: action tags, emotion tags, visual emphasis
        actions = 0
        emotions = 0
        total_segs = 0
        for ep in episodes:
            for scene in ep.get("scenes", []):
                vis = scene.get("visual_emphasis", [])
                for seg in scene.get("content", {}).get("segments", []):
                    total_segs += 1
                    if seg.get("action_tag"):
                        actions += 1
                    if seg.get("emotion_tag"):
                        emotions += 1
        if total_segs == 0:
            return 50
        action_ratio = actions / total_segs
        emotion_ratio = emotions / total_segs
        score = 60
        if action_ratio > 0.2:
            score += 20
        if emotion_ratio > 0.3:
            score += 20
        return min(score, 100)

    def _score_compliance(self, script: dict, input_data: dict) -> int:
        return 85  # Simplified; full implementation checks duration/length targets

    # ── Helpers ──

    def _merge_issues(self, heuristic: list[Issue], llm: list[Issue]) -> list[Issue]:
        """Merge issues, deduplicating by location+category."""
        seen = set()
        merged = []
        for issue in heuristic + llm:
            key = (issue.location, issue.category)
            if key not in seen:
                seen.add(key)
                merged.append(issue)
        return merged

    def _serialize_for_review(self, script: dict) -> dict:
        """Create a compact summary of the script for LLM review."""
        return {
            "global_context_summary": str(script.get("global_context", {}))[:300],
            "episodes": [
                {
                    "episode_index": ep.get("episode_index"),
                    "title": ep.get("title"),
                    "hook": ep.get("hook", ""),
                    "cliffhanger": ep.get("cliffhanger", ""),
                    "scenes": [
                        {
                            "scene_id": sc.get("scene_id"),
                            "location": sc.get("location", {}).get("name"),
                            "mood": sc.get("location", {}).get("mood"),
                            "characters": [c.get("character_ref") for c in sc.get("characters_present", [])],
                            "segment_summary": [
                                {"type": s.get("type"), "text": s.get("text", "")[:60], "emotion": s.get("emotion_tag", ""), "action": s.get("action_tag", "")}
                                for s in sc.get("content", {}).get("segments", [])
                            ],
                        }
                        for sc in ep.get("scenes", [])
                    ],
                }
                for ep in script.get("episodes", [])
            ],
        }

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that may contain markdown or extra content."""
        import re
        match = re.search(r"\{[\s\S]*\}", text)
        return match.group(0) if match else text

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        """Reviewer agents don't revise — they only review."""
        raise NotImplementedError("Reviewer agents cannot revise — only review")
