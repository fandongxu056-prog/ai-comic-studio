"""StyleGuard Agent — reviews scripts for genre/style consistency.

Role: Reviewer
Reviews: ScriptWriter
Focus: Orthogonal to DramaCritic — style/tone/genre, not narrative quality.

Combines heuristic checks (fast, deterministic) with optional LLM deep analysis.
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

    Uses heuristic checks + optional LLM deep analysis.
    """

    def __init__(self, llm_service: Any = None):
        super().__init__(build_style_guard_config())
        self.llm_service = llm_service

    # ── Main Entry ──

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Review script for style compliance."""
        script = input_data.get("script", {})
        style_pref = input_data.get("style_preference", {})
        episodes = script.get("episodes", [])
        llm = (context or {}).get("llm_service", self.llm_service)

        issues: list[Issue] = []
        strengths: list[dict] = []

        # 1. Heuristic checks
        issues.extend(self._check_tone_consistency(episodes))
        issues.extend(self._check_content_safety(episodes, input_data))
        issues.extend(self._check_genre_alignment(episodes, style_pref))
        issues.extend(self._check_dialogue_style(episodes))

        # 2. LLM deep analysis
        if llm and episodes:
            try:
                llm_issues, llm_strengths = await self._llm_review(script, style_pref, llm)
                issues = self._merge_issues(issues, llm_issues)
                strengths.extend(llm_strengths)
            except Exception:
                pass

        # 3. Score
        dimension_scores = {
            "completeness": 90,
            "consistency": self._score_style_consistency(issues),
            "quality": self._score_quality(episodes, issues),
            "executability": 75,
            "compliance": self._score_safety(issues),
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

    def _check_tone_consistency(self, episodes: list) -> list[Issue]:
        """Check emotional tone doesn't fluctuate erratically."""
        issues = []
        for ep in episodes:
            ep_idx = ep.get("episode_index", 0)
            scene_emotions = []
            for scene in ep.get("scenes", []):
                mood = scene.get("location", {}).get("mood", "")
                if mood:
                    scene_emotions.append((scene.get("scene_index", 0), mood))

            # Check for jarring mood swings between adjacent scenes
            for i in range(len(scene_emotions) - 1):
                _, mood_a = scene_emotions[i]
                _, mood_b = scene_emotions[i + 1]

                extreme_pairs = [
                    ("comedy", "tragedy"),
                    ("light", "dark"),
                    ("romantic", "horror"),
                    ("搞笑", "虐心"),
                    ("轻松", "沉重"),
                ]
                for a, b in extreme_pairs:
                    if (mood_a == a and mood_b == b) or (mood_a == b and mood_b == a):
                        issues.append(Issue(
                            id=f"TONE-{ep_idx}-{i}",
                            severity=IssueSeverity.MINOR,
                            location=f"episode={ep_idx}, scenes {scene_emotions[i][0]}-{scene_emotions[i+1][0]}",
                            category="tone_consistency",
                            description=f"场景情绪从'{mood_a}'陡转到'{mood_b}'，可能需要过渡缓冲",
                            evidence=f"Scene {scene_emotions[i][0]} mood: {mood_a} → Scene {scene_emotions[i+1][0]} mood: {mood_b}",
                            suggestion="在两场之间插入一个过渡场景或情绪缓冲segment",
                        ))
        return issues

    def _check_content_safety(self, episodes: list, input_data: dict) -> list[Issue]:
        """Check for prohibited content specified in avoid_elements."""
        avoid = input_data.get("creative_direction", {}).get("avoid_elements", [])
        if not avoid:
            return []

        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                scene_id = scene.get("scene_id", "")
                for seg in scene.get("content", {}).get("segments", []):
                    text = seg.get("text", "")
                    for avoid_item in avoid:
                        if avoid_item and avoid_item in text:
                            issues.append(Issue(
                                id=f"SAFETY-{ep.get('episode_index')}-{scene_id}",
                                severity=IssueSeverity.BLOCKER,
                                location=f"episode={ep.get('episode_index')}, scene={scene_id}",
                                category="content_safety",
                                description=f"包含需要规避的内容: '{avoid_item}'",
                                evidence=f"\"{text[:100]}...\"",
                                suggestion=f"替换或删除涉及'{avoid_item}'的内容",
                            ))
        return issues

    def _check_genre_alignment(self, episodes: list, style_pref: dict) -> list[Issue]:
        """Check that core conflicts match genre expectations."""
        issues = []
        art_style = style_pref.get("art_style", "")
        if not art_style or not episodes:
            return issues

        # Genre-specific keyword expectations
        genre_keywords = {
            "xianxia": ["修炼", "灵气", "境界", "飞升", "法宝", "丹药", "仙"],
            "wuxia": ["内力", "江湖", "剑法", "门派", "侠客", "武林"],
            "urban": ["总裁", "公司", "合同", "CEO", "都市", "豪门"],
            "fantasy": ["魔法", "魔兽", "精灵", "异世界", "召唤"],
            "sci_fi": ["科技", "飞船", "星球", "AI", "赛博", "基因"],
        }

        # For now, just check that at least some genre keywords appear
        relevant_keywords = []
        for genre_key, keywords in genre_keywords.items():
            if genre_key in art_style.lower():
                relevant_keywords.extend(keywords)

        if relevant_keywords:
            all_text = " ".join(
                seg.get("text", "")
                for ep in episodes
                for scene in ep.get("scenes", [])
                for seg in scene.get("content", {}).get("segments", [])
            )
            found = [kw for kw in relevant_keywords if kw in all_text]
            if len(found) < 2 and len(episodes) >= 2:
                issues.append(Issue(
                    id="GENRE-ALIGN",
                    severity=IssueSeverity.MINOR,
                    location="global",
                    category="genre_alignment",
                    description=f"剧本中很少出现{art_style}题材的标志性词汇（仅找到: {found}），可能题材辨识度不足",
                    evidence=f"art_style={art_style}, found_keywords={found}",
                    suggestion=f"在台词或旁白中自然融入题材特有的概念词汇",
                ))

        return issues

    def _check_dialogue_style(self, episodes: list) -> list[Issue]:
        """Check character voices are distinct and genre-appropriate."""
        issues = []
        # Collect dialogue by character
        char_lines: dict[str, list[str]] = {}
        for ep in episodes:
            for scene in ep.get("scenes", []):
                for seg in scene.get("content", {}).get("segments", []):
                    if seg.get("type") == "dialogue" and seg.get("character_ref"):
                        ref = seg["character_ref"]
                        if ref not in char_lines:
                            char_lines[ref] = []
                        char_lines[ref].append(seg.get("text", ""))

        # Flag characters with very few lines
        for ref, lines in char_lines.items():
            if len(lines) <= 2 and len(episodes) >= 3:
                issues.append(Issue(
                    id=f"DIALOG-STYLE-{ref}",
                    severity=IssueSeverity.MINOR,
                    location=f"character={ref}",
                    category="dialogue_style",
                    description=f"角色'{ref}'只有{len(lines)}句对白，可能缺乏存在感",
                    evidence=f"dialogue_count={len(lines)}",
                    suggestion=f"考虑增加'{ref}'的台词或将其合并到其他角色",
                ))

        return issues

    # ── LLM Deep Review ──

    async def _llm_review(
        self, script: dict, style_pref: dict, llm_service: Any
    ) -> tuple[list[Issue], list[dict]]:
        """Use LLM for style-focused analysis."""
        import json

        script_summary = self._serialize_for_review(script)
        art_style = style_pref.get("art_style", "anime")

        system_prompt = f"""你是一位风格把控师，专精于{art_style}题材的内容审核。

请审查以下剧本的风格维度:

1. **题材对齐**:
   - 核心设定和冲突是否符合{art_style}类型的观众预期？
   - 是否有跨类型元素导致定位模糊？

2. **调性一致**:
   - 幽默场景是否出现在合适的位置？
   - 情绪起伏是否合理（不是忽喜忽悲）？

3. **台词风格**:
   - 不同角色的台词是否能通过语气/用词区分？
   - 是否有不符合时代/身份设定的台词？
   - 是否有过于现代化的网络用语出现在古装/玄幻中？

4. **受众匹配**:
   - 内容尺度是否合适？
   - 是否有'出戏'的违和内容？

输出 JSON 格式:
{{
  "issues": [...],
  "strengths": [...]
}}"""

        human_prompt = f"""请审查以下剧本的风格:

---
{json.dumps(script_summary, ensure_ascii=False, indent=2)}
---

输出 JSON 格式的审查结果。"""

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
                    id=f"LLM-STYLE-{item.get('category', 'style')}-{len(issues)+1}",
                    severity=severity,
                    location=item.get("location", ""),
                    category=item.get("category", "style_general"),
                    description=item.get("description", ""),
                    evidence=item.get("evidence", ""),
                    suggestion=item.get("suggestion", ""),
                ))

            strengths = data.get("strengths", [])
            return issues, strengths

        except Exception:
            return [], []

    # ── Scoring Methods ──

    def _score_style_consistency(self, issues: list) -> int:
        base = 90
        base -= len(issues) * 3
        return max(base, 0)

    def _score_quality(self, episodes: list, issues: list) -> int:
        base = 80
        # Boost if lots of emotion/action tags (visual richness)
        total_tags = 0
        total_segs = 0
        for ep in episodes:
            for scene in ep.get("scenes", []):
                for seg in scene.get("content", {}).get("segments", []):
                    total_segs += 1
                    if seg.get("emotion_tag"):
                        total_tags += 1
        if total_segs > 0 and total_tags / total_segs > 0.3:
            base += 10
        return min(base, 100)

    def _score_safety(self, issues: list) -> int:
        blockers = [i for i in issues if i.severity == IssueSeverity.BLOCKER]
        return 0 if blockers else 100

    # ── Helpers ──

    def _merge_issues(self, heuristic: list[Issue], llm: list[Issue]) -> list[Issue]:
        """Merge, deduplicating by location+category."""
        seen = set()
        merged = []
        for issue in heuristic + llm:
            key = (issue.location, issue.category)
            if key not in seen:
                seen.add(key)
                merged.append(issue)
        return merged

    def _serialize_for_review(self, script: dict) -> dict:
        """Create a compact summary for LLM review."""
        return {
            "episodes": [
                {
                    "episode_index": ep.get("episode_index"),
                    "title": ep.get("title"),
                    "scenes": [
                        {
                            "scene_id": sc.get("scene_id"),
                            "location": sc.get("location", {}).get("name"),
                            "mood": sc.get("location", {}).get("mood"),
                            "time_of_day": sc.get("location", {}).get("time_of_day"),
                            "characters": [c.get("character_ref") for c in sc.get("characters_present", [])],
                            "segments": [
                                {
                                    "type": s.get("type"),
                                    "character": s.get("character_ref"),
                                    "text": s.get("text", "")[:80],
                                    "emotion": s.get("emotion_tag"),
                                    "action": s.get("action_tag"),
                                }
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
        import re
        match = re.search(r"\{[\s\S]*\}", text)
        return match.group(0) if match else text

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        raise NotImplementedError("Reviewer agents cannot revise")
