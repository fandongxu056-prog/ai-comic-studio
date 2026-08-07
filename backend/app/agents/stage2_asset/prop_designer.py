"""PropDesigner Agent — designs key props/items from script references.

Role: Author
Reviews from: ConsistencyAuditor
Focus: Key items and recurring props only (one-off props are skipped to save cost)
"""

from app.agents.base import (
    AgentConfig, AgentIdentity, AgentRole, AgentScope,
    BaseAgent, IssueSeverity, ReviewFeedback, ReviewRecord,
)


def build_prop_designer_config() -> AgentConfig:
    return AgentConfig(
        identity=AgentIdentity(
            agent_id="prop_designer_v1",
            identity="道具设计师",
            expertise=["道具功能设计", "材质与工艺", "视觉风格匹配", "比例关系"],
            personality="讲究每一个道具都有其存在的叙事理由和视觉质感",
            blind_spots=["角色设计的细微差别", "大型场景的宏观把握"],
            quality_bias="更关注道具的质感和细节，可能花费过多精力在次要道具上",
        ),
        scope=AgentScope(
            stage="assets",
            reads=["structured_script", "style_preference"],
            writes=["props"],
            must_not_modify=["characters", "locations", "style_manifest"],
        ),
        role=AgentRole.AUTHOR,
        can_be_reviewed_by=["consistency_auditor_v1"],
    )


class PropDesignerAgent(BaseAgent):
    """Designs visual sheets for key and recurring props.

    Only designs important props (key_item + recurring) to control cost.
    One-off props receive auto-generated minimal designs.
    """

    def __init__(self):
        super().__init__(build_prop_designer_config())

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Generate prop design sheets.

        Args:
            input_data: {
                project_id, script: {prop_index},
                style_preference: {art_style}
            }
        """
        script = input_data.get("script", {})
        style_pref = input_data.get("style_preference", {})

        prop_index = script.get("prop_index", {}).get("props", [])
        art_style = style_pref.get("art_style", "anime")

        props = []
        for idx, prop_info in enumerate(prop_index, start=1):
            importance = prop_info.get("importance", "one_off")

            # Skip one-off props — too expensive to design everything
            if importance == "one_off":
                continue

            design = self._design_prop(
                index=idx,
                name=prop_info.get("name", f"prop_{idx}"),
                importance=importance,
                description=prop_info.get("description_from_script", ""),
                art_style=art_style,
            )
            props.append(design)

        return {"props": props}

    def _design_prop(
        self,
        index: int,
        name: str,
        importance: str,
        description: str,
        art_style: str,
    ) -> dict:
        """Design a single prop."""
        prop_id = f"PROP-{index:04d}"

        # Infer material, color, size from description
        material = self._infer_material(name, description)
        color = self._infer_color(name, description)
        size = self._infer_size(name, description)

        # Build prompt template
        prompt_template = (
            f"detailed prop design of {name}, "
            f"{material}, {color}, {size}, "
            f"{description if description else 'highly detailed design'}, "
            f"{art_style} art style, "
            f"product shot, isolated on white background, "
            f"multiple angles, design reference sheet"
        )

        return {
            "prop_id": prop_id,
            "name": name,
            "importance": importance,
            "design": {
                "description": description or f"{name}的详细设计",
                "material": material,
                "color": color,
                "size_hint": size,
                "special_effects": "",
            },
            "reference_image": "",
            "prop_prompt_template": prompt_template,
        }

    def _infer_material(self, name: str, description: str) -> str:
        """Infer material from prop name/description."""
        text = f"{name} {description}".lower()
        if any(w in text for w in ["剑", "刀", "枪", "武器", "金属"]):
            return "金属锻造"
        if any(w in text for w in ["书", "卷", "纸", "信"]):
            return "泛黄纸张"
        if any(w in text for w in ["玉", "宝石", "水晶"]):
            return "玉石/宝石"
        if any(w in text for w in ["木", "杖", "桌", "椅"]):
            return "木材"
        if any(w in text for w in ["药", "瓶", "丹"]):
            return "玻璃/陶瓷"
        return "混合材质"

    def _infer_color(self, name: str, description: str) -> str:
        text = f"{name} {description}".lower()
        if any(w in text for w in ["金", "黄"]):
            return "金色"
        if any(w in text for w in ["银", "白"]):
            return "银色"
        if any(w in text for w in ["黑", "暗", "墨"]):
            return "暗黑色"
        if any(w in text for w in ["红", "血", "朱"]):
            return "深红色"
        return "待定"

    def _infer_size(self, name: str, description: str) -> str:
        text = f"{name} {description}".lower()
        if any(w in text for w in ["剑", "刀", "杖", "枪"]):
            return "约100-120cm长"
        if any(w in text for w in ["书", "卷"]):
            return "约A4大小"
        if any(w in text for w in ["戒指", "耳环", "项链"]):
            return "小型首饰"
        if any(w in text for w in ["瓶", "丹", "药"]):
            return "掌中小瓶"
        return "中等尺寸"

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        revised = dict(original_output)
        revised["version"] = original_output.get("version", 1) + 1
        return revised
