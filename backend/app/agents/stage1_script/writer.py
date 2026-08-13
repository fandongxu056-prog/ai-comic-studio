"""ScriptWriter Agent — generates structured scripts from source material via LLM.

Role: Author
Reviews from: DramaCritic, StyleGuard

Integrates with LLMService for structured output generation.
Post-processes LLM output to inject IDs, timestamps, and auto-computed indexes.
"""

from datetime import datetime, timezone
from typing import Any

from app.agents.base import (
    AgentConfig,
    AgentIdentity,
    AgentRole,
    AgentScope,
    BaseAgent,
    IssueSeverity,
    ReviewFeedback,
    ReviewRecord,
    Verdict,
)
from app.schemas.stage1_script import (
    CharacterIndexEntry,
    LocationIndexEntry,
    PropIndexEntry,
    PropImportance,
    StructuredScript,
)
from app.utils.id_generator import generate_scene_id, generate_script_id


def build_writer_config() -> AgentConfig:
    """Build the ScriptWriter agent configuration."""
    return AgentConfig(
        identity=AgentIdentity(
            agent_id="script_writer_v1",
            identity="资深漫剧编剧",
            expertise=["短剧叙事结构", "爽文节奏", "对白设计", "漫剧改编"],
            personality="敢于打破常规但尊重故事内核，擅长在有限篇幅内制造情绪爆点",
            blind_spots=["对画面可实现性不够敏感", "可能忽略预算约束"],
            quality_bias="更关注戏剧张力而非视觉美感",
        ),
        scope=AgentScope(
            stage="script",
            reads=["project_input", "source_material"],
            writes=["structured_script"],
            must_not_modify=["character_design_sheets", "storyboard"],
        ),
        role=AgentRole.AUTHOR,
        can_be_reviewed_by=["drama_critic_v1", "style_guard_v1"],
    )


class ScriptWriterAgent(BaseAgent):
    """Generates structured scripts (Stage 1 output) via LLM.

    This agent:
    1. Reads the project input and source material
    2. Calls LLM with structured output to generate episodes, scenes, segments
    3. Post-processes: injects IDs, timestamps, auto-computes indexes
    4. Accepts and incorporates review feedback via revise()
    """

    def __init__(self, llm_service: Any = None):
        """Initialize the ScriptWriter agent.

        Args:
            llm_service: LLMService instance for LLM calls.
                         If None, execute() returns a skeleton (offline mode).
        """
        super().__init__(build_writer_config())
        self.llm_service = llm_service

    # ── Main Entry Point ──

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Generate a structured script from source material.

        Args:
            input_data: {
                project_id: str,
                source_material: {type, raw_text, extracted_characters, extracted_locations},
                creative_direction: {adaptation_strategy, narrative_tone, key_themes, ...},
                genre: {primary, sub_tags},
                target_spec: {episode_count, duration_per_episode_seconds, ...},
                style_preference: {art_style, ...},
            }
            context: Optional dict with llm_service override and generation hints.

        Returns:
            StructuredScript as dict (matching docs/schema-design.md).
        """
        # Resolve LLM service (context override > constructor > None)
        llm = (context or {}).get("llm_service", self.llm_service)
        if llm is None:
            return self._skeleton(input_data)

        # Extract inputs
        source = input_data.get("source_material", {})
        creative = input_data.get("creative_direction", {})
        target = input_data.get("target_spec", {})
        genre = input_data.get("genre", {})
        style = input_data.get("style_preference", {})

        project_id = input_data.get("project_id", "")

        # Build prompts
        system_prompt = self._build_system_prompt(genre, creative, target, style)
        human_prompt = self._build_human_prompt(
            source.get("raw_text", ""),
            extracted_chars=source.get("extracted_characters"),
            extracted_locs=source.get("extracted_locations"),
        )

        # Call LLM with inline JSON format (more reliable than Pydantic schema)
        try:
            raw = await llm.generate_text(
                system_prompt=system_prompt,
                human_prompt=human_prompt,
                temperature=0.8,
            )
            import json
            # Extract JSON from response (may have markdown fences)
            data = json.loads(self._extract_json(raw))
            script = StructuredScript.model_validate(data)
        except Exception as e:
            # Fallback: try structured method
            try:
                script = await llm.generate_structured(
                    system_prompt=system_prompt,
                    human_prompt=human_prompt,
                    schema=StructuredScript,
                    temperature=0.8,
                )
            except Exception:
                raise RuntimeError(f"Script generation failed: {e}") from e

        # Post-process
        self._assign_scene_ids(script)
        script.stamp(project_id=project_id, script_id=generate_script_id())
        script = self._ensure_indexes(script)

        return script.model_dump()

    # ── Revision ──

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        """Revise the script based on review feedback.

        - Minor/suggestion issues: auto-fix via LLM
        - Major issues: attempt LLM fix, flag if unresolved
        - Blocker issues: escalate to human
        """
        blockers = [i for i in feedback.critical_issues if i.severity == IssueSeverity.BLOCKER]
        if blockers:
            return {
                "status": "escalated",
                "blockers": [b.model_dump() for b in blockers],
                **original_output,
            }

        llm = self.llm_service
        if llm is None:
            # No LLM available — just bump version
            revised = dict(original_output)
            revised["version"] = original_output.get("version", 1) + 1
            revised["status"] = "draft"
            return revised

        # Build revision prompt
        issues_text = self._format_issues_for_revision(feedback.critical_issues)
        system_prompt = self._build_revision_system_prompt()
        human_prompt = self._build_revision_human_prompt(original_output, issues_text)

        try:
            revised_script: StructuredScript = await llm.generate_structured(
                system_prompt=system_prompt,
                human_prompt=human_prompt,
                schema=StructuredScript,
                temperature=0.6,  # Lower temp for targeted edits
            )
        except Exception:
            # Fallback: return original with version bump
            revised = dict(original_output)
            revised["version"] = original_output.get("version", 1) + 1
            revised["status"] = "draft"
            return revised

        # Preserve server-side metadata
        revised_script.script_id = original_output.get("script_id", "")
        revised_script.project_id = original_output.get("project_id", "")
        revised_script.version = original_output.get("version", 1) + 1
        revised_script.created_at = original_output.get("created_at", "")
        revised_script.updated_at = datetime.now(timezone.utc).isoformat()
        revised_script.status = "draft"

        self._assign_scene_ids(revised_script)
        revised_script = self._ensure_indexes(revised_script)

        # Record review
        self.record_review(ReviewRecord(
            round=len(self.review_history) + 1,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reviewer={"agent_id": "drama_critic_v1", "agent_version": "1.0"},
            verdict=feedback.overall_verdict,
            total_score=feedback.total_score,
            dimension_scores=feedback.dimension_scores,
            issues=[i.model_dump() for i in feedback.critical_issues],
        ))

        return revised_script.model_dump()

    # ── Prompt Building ──

    def _build_system_prompt(
        self,
        genre: dict,
        creative: dict,
        target: dict,
        style: dict | None = None,
    ) -> str:
        """Build the system prompt for script generation.

        Includes the full output schema description so the LLM knows the expected shape.
        """
        genre_primary = genre.get("primary", "drama")
        genre_tags = genre.get("sub_tags", [])
        tone = creative.get("narrative_tone", "快节奏爽文")
        adaptation = creative.get("adaptation_strategy", "original_creation")
        themes = creative.get("key_themes", [])
        avoid = creative.get("avoid_elements", [])
        episodes = target.get("episode_count", 1)
        duration = target.get("duration_per_episode_seconds", 120)
        art = (style or {}).get("art_style", "anime")

        parts = [
            f"你是资深漫剧编剧，专精 **{genre_primary}** 题材的短剧创作。",
            f"视觉风格: {art}",
            "",
            "## 创作要求",
            f"- 叙事基调: {tone}",
            f"- 改编策略: {adaptation}",
            f"- 目标集数: {episodes} 集，每集约 {duration} 秒",
            f"- 格式: 16:9 横屏漫剧（画面优先于文字）",
        ]

        if genre_tags:
            parts.append(f"- 题材标签: {', '.join(genre_tags)}")
        if themes:
            parts.append(f"- 核心主题: {', '.join(themes)}")
        if avoid:
            parts.append(f"- 规避内容: {', '.join(avoid)}")

        parts.extend([
            "",
            "## 剧本结构要求",
            "1. 每集必须有 **hook**（开头30秒内建立悬念）和 **cliffhanger**（结尾留钩子）",
            "2. 每个场景至少包含 **1个冲突点**（信息差/利益冲突/情感对抗）",
            "3. 每句对白必须有叙事功能：推进剧情/揭示性格/建立关系/埋下伏笔",
            "4. 写出 **视觉可表达的内容**——动作、表情、环境变化，而非抽象心理描写",
            "5. 角色对话中注入 **情绪标签**（emotion_tag）和 **动作标注**（action_tag），让画面有依据",
            "",
            "## 输出格式 (严格JSON, 不要markdown代码块, 不要解释)",
            '{',
            '  "global_context": {"story_world": {"setting": "世界观", "era": "时代", "rules": []}, "power_system": {"name": "", "levels": [], "rules": ""}, "timeline": []},',
            '  "episodes": [{',
            '    "episode_index": 1, "title": "标题", "hook": "开头钩子", "cliffhanger": "结尾悬念", "summary": "概要",',
            '    "scenes": [{',
            '      "scene_id": "SC-E001-S001", "scene_index": 1,',
            '      "location": {"name": "地点", "time_of_day": "night", "weather": "", "mood": "紧张"},',
            '      "characters_present": [{"character_ref": "角色名", "emotional_state": "情绪"}],',
            '      "props_mentioned": [], "visual_emphasis": [],',
            '      "content": {"segments": [',
            '        {"type": "narration", "text": "旁白内容"},',
            '        {"type": "dialogue", "character_ref": "说话人", "text": "对白", "emotion_tag": "愤怒", "action_tag": "拍桌"},',
            '        {"type": "action", "text": "动作描述", "action_tag": "拔剑", "emotion_tag": "坚定"},',
            '        {"type": "inner_monologue", "character_ref": "角色", "text": "内心独白"},',
            '      ]}',
            '    }]',
            '  }],',
            '  "character_index": [{"ref_name": "角色名", "role_type": "protagonist", "traits_from_script": ["特征1"]}],',
            '  "location_index": [{"name": "地点名", "scene_count": 1}],',
            '  "prop_index": [{"name": "道具名", "importance": "key_item", "description_from_script": "描述"}]',
            '}',
            "",
            "直接输出上述格式的JSON，不要用```json```包裹。所有内容用中文。",
            "## 中国漫剧特色",
            "- 节奏要快，不要拖沓——前3句话就要抓住观众",
            "- 每集末尾必须有'欲知后事如何'的钩子",
            "- 对白要有'网感'——接地气但有角色辨识度",
            "- 玄幻/仙侠题材注意境界等级的清晰展示",
            "- 情感戏要'甜'或'虐'，不要温吞水",
            "",
            "输出语言: 中文（角色名、地名、对白全部用中文）。JSON 字段名保持英文。",
        ])

        return "\n".join(parts)

    def _build_human_prompt(
        self,
        source_content: str,
        extracted_chars: list | None = None,
        extracted_locs: list | None = None,
    ) -> str:
        """Build the human prompt with source material and extracted hints."""
        # Truncate source to avoid context overflow
        max_source_chars = 8000
        truncated = source_content[:max_source_chars]
        if len(source_content) > max_source_chars:
            truncated += f"\n\n[... 原文共 {len(source_content)} 字，已截取前 {max_source_chars} 字]"

        parts = [
            "请根据以下源材料创作完整的结构化漫剧剧本:",
            "",
            "---",
            truncated,
            "---",
        ]

        if extracted_chars:
            chars_text = "\n".join(
                f"  - {c.get('name', '?')} (角色定位: {c.get('role_hint', 'unknown')})"
                for c in extracted_chars[:10]
            )
            parts.append(f"\n预提取角色（供参考，你可以增删修改）:\n{chars_text}")

        if extracted_locs:
            locs_text = "\n".join(
                f"  - {loc.get('name', '?')}" for loc in extracted_locs[:10]
            )
            parts.append(f"\n预提取场景（供参考，你可以增删修改）:\n{locs_text}")

        parts.append("\n请直接输出完整的 JSON 结构。不要输出其他解释文字。")
        return "\n".join(parts)

    def _build_revision_system_prompt(self) -> str:
        return """你是资深漫剧编剧，正在根据审查反馈修改剧本。

修改原则:
1. 只修改被标记为有问题的部分，保留其他内容完全不变
2. 优先采用审查者给出的修改建议
3. 修改后确保前后连贯——修改一个场景可能影响相邻场景的衔接
4. 如果某个修改建议不合理，保持原样并标注原因
5. version 字段递增 1

输出完整的修改后 JSON 结构。"""

    def _build_revision_human_prompt(self, original_script: dict, issues_text: str) -> str:
        """Build prompt for revision with the original script and issues."""
        import json

        # Serialize only key fields to keep prompt manageable
        summary = {
            "episodes": [
                {
                    "episode_index": ep.get("episode_index"),
                    "title": ep.get("title"),
                    "scenes": [
                        {
                            "scene_id": sc.get("scene_id"),
                            "scene_index": sc.get("scene_index"),
                            "location": sc.get("location", {}).get("name"),
                            "segments": [
                                {"type": s.get("type"), "text": s.get("text", "")[:80]}
                                for s in sc.get("content", {}).get("segments", [])[:5]
                            ],
                        }
                        for sc in ep.get("scenes", [])
                    ],
                }
                for ep in original_script.get("episodes", [])
            ]
        }

        script_text = json.dumps(summary, ensure_ascii=False, indent=2)

        return f"""以下是需要修改的剧本摘要:

---
{script_text}
---

审查发现的问题:
{issues_text}

请修改剧本解决以上问题，输出完整的修改后 JSON。"""

    # ── Post-Processing ──

    def _assign_scene_ids(self, script: StructuredScript) -> None:
        """Auto-assign scene_id for every scene (SC-E{ep:03d}-S{scene:03d})."""
        for ep in script.episodes:
            for i, scene in enumerate(ep.scenes, start=1):
                if not scene.scene_id:
                    scene.scene_id = generate_scene_id(ep.episode_index, i)
                if scene.scene_index == 0:
                    scene.scene_index = i

    def _ensure_indexes(self, script: StructuredScript) -> StructuredScript:
        """Auto-compute character_index, location_index, prop_index from episodes.

        Only fills in indexes that the LLM left empty. If the LLM already provided
        reasonable indexes, they are preserved.
        """
        episodes = script.episodes

        # Character index
        if not script.character_index:
            char_map: dict[str, dict] = {}
            for ep in episodes:
                for scene in ep.scenes:
                    for cp in scene.characters_present:
                        ref = cp.character_ref
                        if ref not in char_map:
                            char_map[ref] = {
                                "ref_name": ref,
                                "role_type": "supporting",
                                "scene_count": 0,
                                "dialogue_count": 0,
                                "first_episode": ep.episode_index,
                                "traits_from_script": [],
                                "relationships": [],
                            }
                        char_map[ref]["scene_count"] += 1
                    for seg in scene.content.segments:
                        if seg.character_ref and seg.character_ref in char_map:
                            char_map[ref]["dialogue_count"] += 1

            # Assign role_type heuristics
            for ref, data in char_map.items():
                if data["scene_count"] >= max(c["scene_count"] for c in char_map.values()) * 0.5:
                    data["role_type"] = "protagonist"
                elif data["scene_count"] <= 2:
                    data["role_type"] = "cameo"
                script.character_index.append(CharacterIndexEntry(**data))

        # Location index
        if not script.location_index:
            loc_map: dict[str, dict] = {}
            for ep in episodes:
                for scene in ep.scenes:
                    name = scene.location.name
                    if name not in loc_map:
                        loc_map[name] = {"name": name, "scene_count": 0, "variations": []}
                    loc_map[name]["scene_count"] += 1
                    time_weather = f"{scene.location.time_of_day or ''}/{scene.location.weather or ''}"
                    if time_weather not in loc_map[name]["variations"] and time_weather != "/":
                        loc_map[name]["variations"].append(time_weather)
            script.location_index = [LocationIndexEntry(**v) for v in loc_map.values()]

        # Prop index
        if not script.prop_index:
            prop_map: dict[str, dict] = {}
            for ep in episodes:
                for scene in ep.scenes:
                    for prop_name in scene.props_mentioned:
                        if prop_name not in prop_map:
                            prop_map[prop_name] = {
                                "name": prop_name,
                                "scene_count": 0,
                                "importance": "one_off",
                                "description_from_script": "",
                            }
                        prop_map[prop_name]["scene_count"] += 1
            # Heuristic: props in 3+ scenes are recurring, 5+ are key items
            for data in prop_map.values():
                if data["scene_count"] >= 5:
                    data["importance"] = PropImportance.KEY_ITEM
                elif data["scene_count"] >= 3:
                    data["importance"] = PropImportance.RECURRING
            script.prop_index = [PropIndexEntry(**v) for v in prop_map.values()]

        return script

    def _format_issues_for_revision(self, issues: list) -> str:
        """Format issue list into a readable revision brief."""
        lines = []
        for i, issue in enumerate(issues, 1):
            lines.append(
                f"{i}. [{issue.severity.value}] {issue.category} @ {issue.location}\n"
                f"   问题: {issue.description}\n"
                f"   证据: {issue.evidence}\n"
                f"   建议: {issue.suggestion or '请自行优化'}\n"
            )
        return "\n".join(lines)

    def _extract_json(self, text: str) -> str:
        """Extract and clean JSON from LLM output (handles common LLM JSON errors)."""
        import re
        # Remove markdown fences
        text = re.sub(r'```(?:json)?\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        # Find the outermost JSON object
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return text
        result = match.group(0)
        # Remove trailing commas (common LLM JSON error)
        result = re.sub(r',\s*}', '}', result)
        result = re.sub(r',\s*]', ']', result)
        return result

    def _parse_raw_output(self, raw_text: str, project_id: str) -> StructuredScript:
        """Attempt to parse unstructured LLM output into StructuredScript."""
        import json
        import re

        # Try to extract JSON block
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                return StructuredScript.model_validate(data)
            except Exception:
                pass

        # Last resort: return minimal valid script
        return StructuredScript(project_id=project_id)

    def _skeleton(self, input_data: dict) -> dict:
        """Return a minimal skeleton when no LLM is available.

        Produces a valid StructuredScript with 1 placeholder episode and scene
        so downstream stages don't break on empty data.
        """
        from app.schemas.stage1_script import (
            CharacterPresent,
            Episode,
            Scene,
            SceneContent,
            SceneLocation,
            ScriptSegment,
            SegmentType,
        )

        project_id = input_data.get("project_id", "")

        placeholder_scene = Scene(
            scene_id="SC-E001-S001",
            scene_index=1,
            location=SceneLocation(name="待定场景"),
            characters_present=[CharacterPresent(character_ref="主角")],
            content=SceneContent(
                segments=[
                    ScriptSegment(type=SegmentType.NARRATION, text="[剧本待生成 — 请配置 LLM API Key 后重试]"),
                ]
            ),
        )

        placeholder_episode = Episode(
            episode_index=1,
            title="待生成",
            scenes=[placeholder_scene],
        )

        script = StructuredScript(
            project_id=project_id,
            episodes=[placeholder_episode],
        )
        script.stamp(project_id=project_id, script_id=generate_script_id())
        return script.model_dump()
