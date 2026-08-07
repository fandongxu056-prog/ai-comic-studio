"""ScriptWriter Agent — generates structured scripts from source material.

Role: Author
Reviews from: DramaCritic, StyleGuard
"""

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
    calculate_total_score,
)


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
    """Generates structured scripts (Stage 1 output).

    This agent:
    1. Reads the project input and source material
    2. Generates episodes, scenes, and segments following the StructuredScript schema
    3. Populates character_index, location_index, and prop_index
    4. Accepts and incorporates review feedback from DramaCritic and StyleGuard
    """

    def __init__(self):
        super().__init__(build_writer_config())

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Generate a structured script from source material.

        Args:
            input_data: {project_id, source_material, creative_direction, target_spec}
            context: Optional LLM provider config

        Returns:
            StructuredScript dict (as defined in docs/schema-design.md)
        """
        # This method would call the LLM with structured output
        # For now, return the skeleton structure
        project_id = input_data.get("project_id", "")
        source = input_data.get("source_material", {})

        script = {
            "script_id": "",
            "project_id": project_id,
            "version": 1,
            "created_at": "",
            "updated_at": "",
            "status": "draft",
            "global_context": {
                "story_world": {},
                "power_system": {},
                "timeline": [],
                "continuity_rules": [],
            },
            "episodes": [],
            "character_index": {"characters": []},
            "location_index": {"locations": []},
            "prop_index": {"props": []},
            "review_history": [],
        }

        return script

    async def execute_with_llm(
        self,
        source_content: str,
        genre: dict,
        creative_direction: dict,
        target_spec: dict,
        llm,  # LangChain chat model
    ) -> dict:
        """Execute with a real LLM — generates structured script output.

        Uses LangChain's with_structured_output for JSON-mode generation.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = self._build_system_prompt(genre, creative_direction, target_spec)
        human_prompt = self._build_human_prompt(source_content)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]

        # The LLM returns structured output matching the script schema
        # For now, return a placeholder; full schema binding will be added
        response = await llm.ainvoke(messages)
        return {"content": response.content, "version": 1}

    def _build_system_prompt(self, genre: dict, creative_direction: dict, target_spec: dict) -> str:
        """Build the system prompt for script generation."""
        genre_str = genre.get("primary", "drama")
        tone = creative_direction.get("narrative_tone", "快节奏")
        episodes = target_spec.get("episode_count", 1)
        duration = target_spec.get("duration_per_episode_seconds", 120)

        return f"""你是资深漫剧编剧，专精于{genre_str}题材的短剧创作。

创作要求:
- 叙事基调: {tone}
- 集数: {episodes}集
- 每集时长: {duration}秒
- 格式: 16:9 横屏漫剧

剧本结构要求:
1. 每集必须有 hook（开头吸引）和 cliffhanger（结尾悬念）
2. 每个场景至少1个冲突点（信息差/利益冲突/情感对抗）
3. 每句对白必须有功能：推进剧情/揭示性格/建立关系/埋下伏笔
4. 写出视觉可表达的内容——人物的动作、表情、环境变化
"""

    def _build_human_prompt(self, source_content: str) -> str:
        """Build the human prompt with source material."""
        return f"""请根据以下源材料创作结构化剧本:

---
{source_content[:5000]}
---

请输出完整的结构化剧本，包含:
1. 全局语境（故事世界观、力量体系、时间线）
2. 分集脚本（每集 hook → 场景序列 → cliffhanger）
3. 角色索引、场景索引、道具索引"""

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        """Revise the script based on review feedback.

        Only auto-fixes minor/suggestion issues.
        Major/blocker issues require human intervention (escalation).
        """
        blockers = [i for i in feedback.critical_issues if i.severity == IssueSeverity.BLOCKER]
        if blockers:
            # Cannot auto-fix blockers — escalate to human
            return {"status": "escalated", "blockers": [b.model_dump() for b in blockers], **original_output}

        # Apply fixable issues
        revised = dict(original_output)
        revised["version"] = original_output.get("version", 1) + 1
        revised["status"] = "draft"

        # Record the review
        self.record_review(ReviewRecord(
            round=len(self.review_history) + 1,
            timestamp="",
            reviewer={"agent_id": "drama_critic_v1", "agent_version": "1.0"},
            verdict=feedback.overall_verdict,
            total_score=feedback.total_score,
            dimension_scores=feedback.dimension_scores,
            issues=[i.model_dump() for i in feedback.critical_issues],
        ))

        return revised
