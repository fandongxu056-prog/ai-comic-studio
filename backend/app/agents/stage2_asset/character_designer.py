"""CharacterDesigner Agent — generates character visual design sheets via LLM."""

from typing import Any
from app.agents.base import AgentConfig, AgentIdentity, AgentRole, AgentScope, BaseAgent, ReviewFeedback
from app.schemas.stage2_asset import CharacterAsset
from app.utils.id_generator import generate_character_id, generate_costume_id


class CharacterDesignerAgent(BaseAgent):
    def __init__(self, llm_service: Any = None):
        super().__init__(AgentConfig(
            identity=AgentIdentity(agent_id="character_designer_v1", identity="资深角色设计师",
                expertise=["动漫角色设计", "服装设计", "表情设计"], personality="善于从文字中提取视觉特征",
                blind_spots=["可能忽略场景道具的关联性"], quality_bias="更关注角色辨识度"),
            scope=AgentScope(stage="assets", reads=["script", "style_preference"], writes=["characters"]),
            role=AgentRole.AUTHOR, can_be_reviewed_by=["consistency_auditor_v1"],
        ))
        self.llm_service = llm_service

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        llm = (context or {}).get("llm_service", self.llm_service)
        script = input_data.get("script", {})
        style = input_data.get("style_preference", {})
        char_index = script.get("character_index", [])

        if not char_index:
            return {"characters": []}

        if llm:
            try:
                from pydantic import BaseModel
                class CharList(BaseModel):
                    characters: list[CharacterAsset]
                result = await llm.generate_structured(
                    self._build_system_prompt(style),
                    self._build_human_prompt(char_index),
                    CharList, temperature=0.8,
                )
                chars = result.characters
            except Exception:
                chars = self._heuristic(char_index)
        else:
            chars = self._heuristic(char_index)

        for i, c in enumerate(chars, start=1):
            if not c.character_id:
                c.character_id = generate_character_id(i)
            for j, cost in enumerate(c.design_sheet.costumes, start=1):
                if not cost.costume_id:
                    cost.costume_id = generate_costume_id(j)

        return {"characters": [c.model_dump() for c in chars]}

    def _heuristic(self, char_index: list) -> list[CharacterAsset]:
        from app.schemas.stage2_asset import Costume
        results = []
        for i, c in enumerate(char_index, start=1):
            char = CharacterAsset(
                character_id=generate_character_id(i),
                ref_name=c.get("ref_name", f"角色{i}"),
                role_type=c.get("role_type", "supporting"),
                character_prompt_template=f"{c.get('ref_name','')} character, anime art style, clean linework, flat color illustration",
            )
            if not char.design_sheet.costumes:
                char.design_sheet.costumes = [Costume(costume_id=generate_costume_id(1), name="默认服装", description="待LLM生成")]
            results.append(char)
        return results

    def _build_system_prompt(self, style: dict) -> str:
        art = (style or {}).get("art_style", "anime")
        return f"""你是资深动漫角色设计师({art}风格)。为每个角色创建视觉设计。

输出每个角色的:
1. appearance: age_appearance/gender/body_type/height_cm + face(shape/eyes/nose/mouth/skin_tone) + hair(color/style/length) + distinguishing_features(至少2个识别特征)
2. costumes: 至少1套服装(name/description/color_palette/accessories)
3. expressions: 7种中文表情描述(neutral/happy/angry/sad/surprised/scheming/cold)
4. character_prompt_template: 英文生图提示词, 包含art style/anime关键词, 可稳定复现该角色
5. voice_profile: {{gender, age_range, tone, tts_voice_id:""}}

设计原则: 每个角色独特辨识特征; prompt_template含风格一致性关键词; 主角设计让人一眼记住"""

    def _build_human_prompt(self, char_index: list) -> str:
        import json
        summary = [{"ref_name": c.get("ref_name"), "role_type": c.get("role_type"), "traits": c.get("traits_from_script", [])} for c in char_index]
        return f"为以下角色创建视觉设计:\n{json.dumps(summary, ensure_ascii=False, indent=2)}"

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        return {"status": "escalated", **original_output}
