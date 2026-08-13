"""SceneDesigner Agent — generates location visual design sheets via LLM."""

from typing import Any
from app.agents.base import AgentConfig, AgentIdentity, AgentRole, AgentScope, BaseAgent, ReviewFeedback
from app.schemas.stage2_asset import LocationAsset
from app.utils.id_generator import generate_location_id


class SceneDesignerAgent(BaseAgent):
    def __init__(self, llm_service: Any = None):
        super().__init__(AgentConfig(
            identity=AgentIdentity(agent_id="scene_designer_v1", identity="资深场景设计师",
                expertise=["场景空间设计", "氛围营造", "光线设计"], personality="善于构建有情绪的空间",
                blind_spots=["可能忽略与角色的比例关系"], quality_bias="更关注氛围而非功能性"),
            scope=AgentScope(stage="assets", reads=["script", "style_preference"], writes=["locations"]),
            role=AgentRole.AUTHOR, can_be_reviewed_by=["consistency_auditor_v1"],
        ))
        self.llm_service = llm_service

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        llm = (context or {}).get("llm_service", self.llm_service)
        script = input_data.get("script", {})
        style = input_data.get("style_preference", {})
        loc_index = script.get("location_index", [])

        if not loc_index:
            return {"locations": []}

        # Collect scene context from episodes for richer LLM input
        scene_context = self._collect_scene_context(script.get("episodes", []))

        if llm:
            try:
                from pydantic import BaseModel
                class LocList(BaseModel):
                    locations: list[LocationAsset]
                result = await llm.generate_structured(
                    self._build_system_prompt(style),
                    self._build_human_prompt(loc_index, scene_context),
                    LocList, temperature=0.7,
                )
                locs = result.locations
            except Exception:
                locs = self._heuristic(loc_index, scene_context)
        else:
            locs = self._heuristic(loc_index, scene_context)

        for i, loc in enumerate(locs, start=1):
            if not loc.location_id:
                loc.location_id = generate_location_id(i)
            # Ensure prompt template has style keywords
            if "anime" not in loc.location_prompt_template.lower():
                loc.location_prompt_template += ", anime background art"

        return {"locations": [l.model_dump() for l in locs]}

    def _heuristic(self, loc_index: list, scene_context: dict) -> list[LocationAsset]:
        results = []
        for i, loc in enumerate(loc_index, start=1):
            name = loc.get("name", f"场景{i}")
            ctx = scene_context.get(name, {})
            results.append(LocationAsset(
                location_id=generate_location_id(i),
                name=name,
                location_prompt_template=f"{name}, anime background art, detailed environment, atmospheric lighting",
            ))
        return results

    def _collect_scene_context(self, episodes: list) -> dict:
        """Collect time_of_day/weather/mood per location from all episodes."""
        ctx: dict[str, dict] = {}
        for ep in episodes:
            for sc in ep.get("scenes", []):
                loc_name = sc.get("location", {}).get("name", "")
                if loc_name not in ctx:
                    ctx[loc_name] = {"times": set(), "weathers": set(), "moods": set()}
                loc = sc.get("location", {})
                if loc.get("time_of_day"):
                    ctx[loc_name]["times"].add(loc["time_of_day"])
                if loc.get("weather"):
                    ctx[loc_name]["weathers"].add(loc["weather"])
                if loc.get("mood"):
                    ctx[loc_name]["moods"].add(loc["mood"])
        return ctx

    def _build_system_prompt(self, style: dict) -> str:
        art = (style or {}).get("art_style", "anime")
        return f"""你是资深动漫场景设计师({art}风格)。为每个场景创建设计:

每个场景输出:
1. design_sheet: description(场景空间描述200字)/key_features(4-6个视觉特征)/layout_notes(空间布局说明)/variations(不同时间/天气的变体)
2. location_prompt_template: 英文生图提示词(含anime background art关键词,可稳定复现该场景)

设计原则: key_features精准描述视觉特征供生图用; layout_notes说明人物站哪/遮挡物; variations覆盖所有出现的time_of_day和weather; prompt_template可独立使用"""

    def _build_human_prompt(self, loc_index: list, scene_context: dict) -> str:
        import json
        summary = []
        for loc in loc_index:
            name = loc.get("name", "")
            ctx = scene_context.get(name, {})
            summary.append({
                "name": name,
                "scene_count": loc.get("scene_count", 0),
                "times_of_day": list(ctx.get("times", [])),
                "weathers": list(ctx.get("weathers", [])),
                "moods": list(ctx.get("moods", [])),
            })
        return f"为以下场景创建视觉设计:\n{json.dumps(summary, ensure_ascii=False, indent=2)}"

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        return {"status": "escalated", **original_output}
