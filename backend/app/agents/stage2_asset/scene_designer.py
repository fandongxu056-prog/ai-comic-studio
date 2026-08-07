"""SceneDesigner Agent — generates scene/location visual design sheets.

Role: Author
Reviews from: ConsistencyAuditor
"""

from app.agents.base import (
    AgentConfig, AgentIdentity, AgentRole, AgentScope,
    BaseAgent, Issue, IssueSeverity, ReviewFeedback, ReviewRecord, Verdict,
)


def build_scene_designer_config() -> AgentConfig:
    return AgentConfig(
        identity=AgentIdentity(
            agent_id="scene_designer_v1",
            identity="场景视觉设计师",
            expertise=["环境设计", "空间布局", "光影氛围", "漫剧场景"],
            personality="擅长用空间语言讲故事——场景本身即是叙事元素",
            blind_spots=["角色外貌细节", "道具精细度"],
            quality_bias="更关注场景的氛围感和大关系，可能忽略细微的空间逻辑",
        ),
        scope=AgentScope(
            stage="assets",
            reads=["structured_script", "style_preference"],
            writes=["locations"],
            must_not_modify=["characters", "props", "style_manifest"],
        ),
        role=AgentRole.AUTHOR,
        can_be_reviewed_by=["consistency_auditor_v1"],
    )


class SceneDesignerAgent(BaseAgent):
    """Designs visual sheets for all locations in the script.

    For each location in script.location_index, generates:
    - description with key visual features
    - layout_notes for shot composition reference
    - variations (time_of_day × weather combinations)
    - location_prompt_template for stable image generation
    """

    def __init__(self):
        super().__init__(build_scene_designer_config())

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Generate scene design sheets from script location data.

        Args:
            input_data: {
                project_id, script: {location_index, episodes[].scenes[].location},
                style_preference, consistency_requirements
            }
        """
        script = input_data.get("script", {})
        style_pref = input_data.get("style_preference", {})
        loc_index = script.get("location_index", {}).get("locations", [])

        # Collect all time_of_day/weather combinations from actual scenes
        scene_variations = self._collect_scene_variations(script.get("episodes", []))

        locations = []
        for idx, loc_info in enumerate(loc_index, start=1):
            loc_name = loc_info.get("name", f"location_{idx}")
            variations_needed = scene_variations.get(loc_name, [{"time": "unspecified", "weather": "clear"}])

            design = self._design_location(
                index=idx,
                name=loc_name,
                scene_count=loc_info.get("scene_count", 0),
                variations_needed=variations_needed,
                art_style=style_pref.get("art_style", "anime"),
            )
            locations.append(design)

        return {"locations": locations}

    def _design_location(
        self,
        index: int,
        name: str,
        scene_count: int,
        variations_needed: list[dict],
        art_style: str,
    ) -> dict:
        """Design a single location's visual sheet."""
        location_id = f"LOC-{index:04d}"

        # Build base description
        description, key_features = self._build_location_description(name, art_style)

        # Build layout notes for shot composition
        layout_notes = self._build_layout_notes(name, scene_count)

        # Build variations
        variations = self._build_variations(variations_needed, description)

        # Build prompt template
        prompt_template = self._build_prompt_template(name, description, key_features, art_style)

        return {
            "location_id": location_id,
            "name": name,
            "design_sheet": {
                "description": description,
                "key_features": key_features,
                "layout_notes": layout_notes,
                "variations": variations,
            },
            "reference_images": {
                "wide_establishing": "",
                "medium_angle": "",
                "detail_shots": [],
            },
            "location_prompt_template": prompt_template,
        }

    def _build_location_description(self, name: str, art_style: str) -> tuple[str, list[str]]:
        """Build a location description with key visual features.

        Returns (description, key_features_list)
        """
        # In production, LLM generates this from scene context
        description = f"{name}的场景空间设计，采用{art_style}风格"
        key_features = [
            f"{name}的标志性建筑/装饰元素",
            "主色调和材质",
            "光源方向和色温",
            "空间尺度感",
        ]
        return description, key_features

    def _build_layout_notes(self, name: str, scene_count: int) -> str:
        """Build spatial layout notes for shot composition reference."""
        return f"""场景 '{name}' 的空间布局:
- 主要活动区域位置和范围
- 角色通常站位（根据对话关系调整）
- 自然遮挡物（柱子、帷幕、家具等可用于构图）
- 空间深度感（前景/中景/远景层次）
- 此场景在 {scene_count} 场戏中出现，保持空间一致性"""

    def _build_variations(self, variations_needed: list[dict], base_description: str) -> list[dict]:
        """Build location variations for time/weather combinations."""
        variations = []
        seen = set()
        for var in variations_needed:
            key = f"{var.get('time', 'day')}_{var.get('weather', 'clear')}"
            if key in seen:
                continue
            seen.add(key)

            time_modifier = {
                "dawn": "黎明的金色晨光",
                "morning": "柔和的上午光线",
                "noon": "强烈的正午顶光",
                "afternoon": "温暖的午后斜阳",
                "evening": "橘红色的黄昏逆光",
                "night": "月光和人工灯光的冷色调",
                "midnight": "深沉的午夜暗光，只有微弱光源",
            }.get(var.get("time", "day"), "自然日光")

            weather_modifier = {
                "clear": "晴朗",
                "rain": "雨天的湿润反光和灰调色彩",
                "snow": "雪景的白色覆盖和柔和散射光",
                "fog": "雾天的低能见度和神秘氛围",
                "storm": "暴风雨的戏剧性闪电和暗云",
                "wind": "大风天气的动态植被和衣摆",
            }.get(var.get("weather", "clear"), "")

            variations.append({
                "variation_id": f"VAR-{len(variations)+1:03d}",
                "condition": f"{var.get('time', 'day')}_{var.get('weather', 'clear')}",
                "description_modifier": f"{time_modifier}，{weather_modifier}",
            })

        return variations

    def _build_prompt_template(
        self, name: str, description: str, key_features: list[str], art_style: str
    ) -> str:
        """Build stable prompt template for this location."""
        features_str = ", ".join(key_features[:3])
        return (
            f"wide establishing shot of {name}, "
            f"{features_str}, "
            f"{art_style} art style, "
            f"cinematic composition, detailed environment, atmospheric lighting, "
            f"no characters, empty scene, clean background"
        )

    def _collect_scene_variations(self, episodes: list) -> dict[str, list[dict]]:
        """Collect all time_of_day/weather combos for each location from scenes."""
        variations: dict[str, list[dict]] = {}
        for ep in episodes:
            for scene in ep.get("scenes", []):
                loc_name = scene.get("location", {}).get("name", "")
                if not loc_name:
                    continue
                time = scene.get("location", {}).get("time_of_day", "day")
                weather = scene.get("location", {}).get("weather", "clear")
                if loc_name not in variations:
                    variations[loc_name] = []
                variations[loc_name].append({"time": time, "weather": weather})
        return variations

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        """Revise scene designs based on audit feedback."""
        revised = dict(original_output)
        revised["version"] = original_output.get("version", 1) + 1

        blockers = [i for i in feedback.critical_issues if i.severity == IssueSeverity.BLOCKER]
        if blockers:
            return {"status": "escalated", "blockers": [b.model_dump() for b in blockers], **revised}

        self.record_review(ReviewRecord(
            round=len(self.review_history) + 1,
            timestamp="",
            reviewer={"agent_id": "consistency_auditor_v1", "agent_version": "1.0"},
            verdict=feedback.overall_verdict,
            total_score=feedback.total_score,
            dimension_scores=feedback.dimension_scores,
            issues=[i.model_dump() for i in feedback.critical_issues],
        ))
        return revised
