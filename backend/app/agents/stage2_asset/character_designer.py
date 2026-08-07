"""CharacterDesigner Agent — generates character visual design sheets from script data.

Role: Author
Reviews from: ConsistencyAuditor
Design reference: docs/agent-collaboration-protocol.md §3
"""

from app.agents.base import (
    AgentConfig, AgentIdentity, AgentRole, AgentScope,
    BaseAgent, Issue, IssueSeverity, ReviewFeedback, ReviewRecord,
    Verdict,
)


def build_character_designer_config() -> AgentConfig:
    return AgentConfig(
        identity=AgentIdentity(
            agent_id="character_designer_v1",
            identity="角色视觉设计师",
            expertise=["角色外貌设计", "服装设计", "表情设计", "视觉辨识度", "漫剧角色"],
            personality="擅长从文字描述中提炼视觉特征，重视角色辨识度和功能性",
            blind_spots=["场景空间布局", "道具功能性细节"],
            quality_bias="更关注角色的视觉冲击力和记忆点，可能忽略动画可实现性",
        ),
        scope=AgentScope(
            stage="assets",
            reads=["structured_script", "style_preference"],
            writes=["characters"],
            must_not_modify=["locations", "props", "style_manifest"],
        ),
        role=AgentRole.AUTHOR,
        can_be_reviewed_by=["consistency_auditor_v1"],
    )


class CharacterDesignerAgent(BaseAgent):
    """Designs character visual sheets for all characters in the script.

    For each character in the script's character_index, generates:
    - appearance (face, body, hair, distinguishing features)
    - costumes (linked to specific scenes)
    - expressions (at minimum: neutral, happy, angry, sad, surprised)
    - character_prompt_template (for stable image generation)
    - voice_profile (for TTS in Stage 4)
    """

    def __init__(self):
        super().__init__(build_character_designer_config())

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Generate character design sheets from script data.

        Args:
            input_data: {
                project_id: str,
                script: StructuredScript (character_index + scene data),
                style_preference: {art_style, color_palette, reference_images, style_notes},
                consistency_requirements: {global_style_seed, character_style_notes}
            }
            context: Optional LLM config

        Returns:
            dict with 'characters' key containing list of character design sheets
        """
        script = input_data.get("script", {})
        style_pref = input_data.get("style_preference", {})
        consistency = input_data.get("consistency_requirements", {})

        char_index = script.get("character_index", {}).get("characters", [])
        style_manifest = self._derive_style_manifest(style_pref)

        characters = []
        for idx, char_info in enumerate(char_index, start=1):
            design = self._design_character(
                index=idx,
                ref_name=char_info.get("ref_name", f"character_{idx}"),
                role_type=char_info.get("role_type", "supporting"),
                traits=char_info.get("traits_from_script", []),
                scene_count=char_info.get("scene_count", 0),
                relationships=char_info.get("relationships", []),
                art_style=style_pref.get("art_style", "anime"),
                global_style_notes=consistency.get("character_style_notes", ""),
            )
            characters.append(design)

        # Validate: no two characters look too similar
        differentiation_issues = self._check_character_differentiation(characters)
        if differentiation_issues:
            # Auto-apply fixes for minor differentiation issues
            pass

        return {
            "characters": characters,
            "differentiation_warnings": [i.model_dump() for i in differentiation_issues],
        }

    def _design_character(
        self,
        index: int,
        ref_name: str,
        role_type: str,
        traits: list[str],
        scene_count: int,
        relationships: list[dict],
        art_style: str,
        global_style_notes: str,
    ) -> dict:
        """Design a single character's visual sheet.

        Each design includes:
        - Structured appearance (face, body, hair, features)
        - Costume set (linked to scenes via scenes_used_in)
        - Expression palette (minimum 5 expressions)
        - Prompt template for stable diffusion
        - Voice profile for TTS
        """
        character_id = f"CHAR-{index:04d}"

        # Build appearance from traits
        appearance = self._build_appearance(traits, role_type, art_style)

        # Build costumes (at least 1 default, more for major characters)
        costumes = self._build_costumes(index, role_type, scene_count, appearance)

        # Build expression palette
        expressions = self._build_expressions(role_type, traits)

        # Build stable prompt template
        prompt_template = self._build_prompt_template(
            ref_name, appearance, art_style, global_style_notes
        )

        # Build voice profile
        voice_profile = self._build_voice_profile(role_type, traits)

        return {
            "character_id": character_id,
            "ref_name": ref_name,
            "full_name": ref_name,  # Will be refined with LLM
            "role_type": role_type,
            "design_sheet": {
                "appearance": appearance,
                "costumes": costumes,
                "expressions": expressions,
                "pose_notes": f"{role_type}角色的标准站姿和体态特征 — 将根据{art_style}风格调整",
            },
            "reference_images": {
                "full_body_front": "",
                "full_body_back": "",
                "portrait": "",
                "expression_sheet": "",
                "costume_variants": {},
            },
            "character_prompt_template": prompt_template,
            "voice_profile": voice_profile,
        }

    def _build_appearance(self, traits: list[str], role_type: str, art_style: str) -> dict:
        """Build structured appearance from character traits."""
        return {
            "age_appearance": "25-30岁",  # LLM would infer this from traits
            "gender": "男",                # LLM would infer this
            "height_cm": 175,
            "body_type": "标准",
            "face": {
                "shape": "瓜子脸",
                "eyes": "丹凤眼，眼尾微挑",
                "nose": "直鼻",
                "mouth": "薄唇",
                "skin_tone": "白皙",
                "overall_description": f"基于以下特征生成: {', '.join(traits[:3]) if traits else '待设计'}",
            },
            "hair": {
                "color": "黑色",
                "style": "长发束起",
                "length": "及腰",
            },
            "distinguishing_features": [
                "左眼角下方的泪痣",
                "右手无名指有一枚银色戒指",
            ],
        }

    def _build_costumes(
        self, char_index: int, role_type: str, scene_count: int, appearance: dict
    ) -> list[dict]:
        """Build costume designs — at least 1, more for major characters."""
        costumes = []

        # Default costume
        costumes.append({
            "costume_id": f"COST-{char_index:04d}",
            "name": "默认服装",
            "description": f"基于角色外貌设计的标准服装",
            "scenes_used_in": [],
            "color_palette": ["#1a1a2e", "#e94560", "#ffffff"],
            "accessories": [],
            "season": "通用",
        })

        # Major characters get an alternate costume
        if role_type in ("protagonist", "antagonist"):
            costumes.append({
                "costume_id": f"COST-{char_index:04d}a",
                "name": "战斗/正式服装",
                "description": f"{role_type}角色在关键场景的替换服装",
                "scenes_used_in": [],
                "color_palette": ["#0f3460", "#e94560", "#16213e"],
                "accessories": [],
                "season": "通用",
            })

        return costumes

    def _build_expressions(self, role_type: str, traits: list[str]) -> dict:
        """Build expression palette — minimum 5 expressions."""
        return {
            "neutral": "面无表情，直视前方，嘴唇微抿",
            "happy": "眼角微弯，嘴角上扬，面部肌肉自然放松",
            "angry": "眉毛紧锁，目光锐利，嘴角下拉",
            "sad": "眼眶微红，视线向下，嘴角微微下垂",
            "surprised": "眼睛微睁大，眉毛上挑，嘴唇微张",
            "scheming": "嘴角一侧上扬，眼神略带算计",
            "cold": "目光如冰，面部肌肉无任何波动，下颌微微收紧",
        }

    def _build_prompt_template(
        self, name: str, appearance: dict, art_style: str, style_notes: str
    ) -> str:
        """Build a stable prompt template for image generation."""
        face = appearance.get("face", {})
        hair = appearance.get("hair", {})
        features = appearance.get("distinguishing_features", [])

        template = (
            f"character design sheet of {name}, "
            f"{face.get('overall_description', '')}, "
            f"{hair.get('color', '')} {hair.get('style', '')} {hair.get('length', '')} hair, "
            f"{face.get('eyes', '')}, "
            f"{face.get('skin_tone', '')} skin, "
        )
        if features:
            template += f"distinctive features: {', '.join(features[:2])}, "
        template += f"{art_style} art style, full body, standing pose, clean lines, character reference sheet, white background"

        if style_notes:
            template += f", {style_notes}"

        return template

    def _build_voice_profile(self, role_type: str, traits: list[str]) -> dict:
        """Build voice profile for TTS."""
        return {
            "gender": "男" if role_type in ("protagonist", "antagonist") else "女",
            "age_range": "25-35",
            "tone": "沉稳有力" if role_type == "protagonist" else "尖细阴冷" if role_type == "antagonist" else "自然",
            "pace": "中速",
            "tts_voice_id": "",  # Set when TTS provider is configured
        }

    def _derive_style_manifest(self, style_pref: dict) -> dict:
        """Derive a style manifest from project preferences."""
        return {
            "art_style": style_pref.get("art_style", "anime"),
            "global_style_seed": 42,  # Will be set from seed_manager
            "color_palette": {
                "name": "custom",
                "primary_colors": ["#1a1a2e", "#e94560", "#0f3460"],
                "accent_colors": ["#f5f5f5", "#ffd700"],
                "mood_colors": {
                    "happy": "#ffd700",
                    "sad": "#4a4e69",
                    "tense": "#e94560",
                    "romantic": "#f28482",
                    "dark": "#1a1a2e",
                },
            },
            "line_style": "clean",
            "lighting_default": "soft cinematic lighting",
            "global_negative_prompt": "blurry, low quality, deformed face, extra limbs, ugly, watermark, text",
        }

    def _check_character_differentiation(self, characters: list[dict]) -> list[Issue]:
        """CROSS-S2-000: Check that no two characters look too similar."""
        issues = []
        for i in range(len(characters)):
            for j in range(i + 1, len(characters)):
                char_a = characters[i]
                char_b = characters[j]
                # Compare hair color + face shape + skin tone
                hair_a = char_a["design_sheet"]["appearance"]["hair"]["color"]
                hair_b = char_b["design_sheet"]["appearance"]["hair"]["color"]
                face_a = char_a["design_sheet"]["appearance"]["face"]["shape"]
                face_b = char_b["design_sheet"]["appearance"]["face"]["shape"]

                if hair_a == hair_b and face_a == face_b:
                    issues.append(Issue(
                        id=f"DIFF-{char_a['character_id']}-{char_b['character_id']}",
                        severity=IssueSeverity.MAJOR,
                        location=f"characters: {char_a['ref_name']}, {char_b['ref_name']}",
                        category="character_differentiation",
                        description=f"{char_a['ref_name']} 和 {char_b['ref_name']} 外貌过于相似",
                        evidence=f"相同发型颜色({hair_a}) + 相同脸型({face_a})",
                        suggestion="调整其中一位的发型颜色、增加或减少面部识别特征、或改变体型差异",
                    ))
        return issues

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        """Revise character designs based on consistency audit feedback."""
        revised = dict(original_output)
        revised["version"] = original_output.get("version", 1) + 1

        auto_fixable = [i for i in feedback.critical_issues if self.can_auto_fix(i)]
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
