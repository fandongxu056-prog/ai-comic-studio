"""ConsistencyAuditor Agent — reviews all Stage 2 assets for cross-asset consistency.

Role: Reviewer (single reviewer for all 3 author agents)
Reviews: CharacterDesigner, SceneDesigner, PropDesigner

This is THE most critical reviewer in the pipeline.
Asset consistency errors here will cascade into Stage 3 & 4 failures.
Hence Stage 2's QC weight on consistency is 40%.
"""

from app.agents.base import (
    AgentConfig, AgentIdentity, AgentRole, AgentScope,
    BaseAgent, Issue, IssueSeverity, ReviewFeedback, Verdict,
    calculate_total_score, QC_WEIGHTS,
)


def build_consistency_auditor_config() -> AgentConfig:
    return AgentConfig(
        identity=AgentIdentity(
            agent_id="consistency_auditor_v1",
            identity="资产一致性审查师",
            expertise=["风格统一性", "色彩协调", "比例关系", "跨资产引用一致性"],
            personality="极其注重细节，会在脑内将所有资产放在同一画面中比对",
            blind_spots=["创意品质判断（不是创意评审，只审一致性）"],
            quality_bias="宁可多报也不会放过一个不一致——漏报比多报更致命",
        ),
        scope=AgentScope(
            stage="assets",
            reads=["characters", "locations", "props", "style_manifest", "script"],
            writes=["review_feedback"],
            must_not_modify=["characters", "locations", "props"],
        ),
        role=AgentRole.REVIEWER,
        can_review=["character_designer_v1", "scene_designer_v1", "prop_designer_v1"],
    )


class ConsistencyAuditorAgent(BaseAgent):
    """Reviews all Stage 2 assets for cross-asset visual consistency.

    Checklist (from agent-collaboration-protocol.md §3.2):
    Round 1:
    - Style uniformity across all assets
    - Scale/proportion relationships
    - Color harmony
    - Asset coverage completeness

    Round 2:
    - Costume-face consistency within same character
    - Prompt template compatibility
    """

    def __init__(self):
        super().__init__(build_consistency_auditor_config())

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Audit all Stage 2 assets for consistency.

        Args:
            input_data: {
                characters: list of character design sheets,
                locations: list of location design sheets,
                props: list of prop design sheets,
                style_manifest: {art_style, color_palette, ...},
                script: {character_index, location_index, prop_index}
            }
        """
        characters = input_data.get("characters", [])
        locations = input_data.get("locations", [])
        props = input_data.get("props", [])
        style_manifest = input_data.get("style_manifest", {})
        script = input_data.get("script", {})

        issues: list[Issue] = []
        strengths: list[dict] = []

        # Round 1: Broad consistency checks
        issues.extend(self._check_style_uniformity(characters, locations, props, style_manifest))
        issues.extend(self._check_character_differentiation(characters))
        issues.extend(self._check_scale_proportion(characters, locations, props))
        issues.extend(self._check_color_harmony(characters, locations, style_manifest))
        issues.extend(self._check_asset_coverage(characters, locations, props, script))

        # Round 2: Detail consistency
        issues.extend(self._check_costume_face_consistency(characters))
        issues.extend(self._check_prompt_compatibility(characters, locations, style_manifest))

        # Scoring (Stage 2 weights: consistency = 40%)
        dimension_scores = {
            "completeness": self._score_coverage(characters, locations, props, script),
            "consistency": self._score_consistency(issues),
            "quality": self._score_design_quality(characters, locations),
            "executability": self._score_prompt_quality(characters, locations),
            "compliance": self._score_style_compliance(style_manifest),
        }

        total_score = calculate_total_score(dimension_scores, "assets")
        blocker_count = sum(1 for i in issues if i.severity == IssueSeverity.BLOCKER)

        if total_score >= 80 and blocker_count == 0:
            verdict = Verdict.APPROVED
        elif 65 <= total_score < 80 and blocker_count == 0:
            verdict = Verdict.APPROVED_WITH_MINOR
        else:
            verdict = Verdict.NEEDS_REVISION

        feedback = ReviewFeedback(
            overall_verdict=verdict,
            total_score=total_score,
            dimension_scores=dimension_scores,
            critical_issues=issues,
            strengths=strengths,
        )

        return feedback.model_dump()

    # ── Round 1 Checks ──

    def _check_style_uniformity(
        self,
        characters: list,
        locations: list,
        props: list,
        style_manifest: dict,
    ) -> list[Issue]:
        """Check all assets share the same visual language."""
        issues = []
        art_style = style_manifest.get("art_style", "anime")

        # Check all character prompts include art style
        for char in characters:
            prompt = char.get("character_prompt_template", "")
            if art_style not in prompt:
                issues.append(Issue(
                    id=f"STYLE-{char.get('character_id', '')}",
                    severity=IssueSeverity.MAJOR,
                    location=f"character: {char.get('ref_name', '')}",
                    category="style_uniformity",
                    description=f"角色 {char.get('ref_name')} 的提示词模板未包含风格声明",
                    evidence=f"prompt中缺少 '{art_style}'",
                    suggestion=f"在 prompt_template 末尾添加 '{art_style} art style'",
                ))

        # Check locations too
        for loc in locations:
            prompt = loc.get("location_prompt_template", "")
            if art_style not in prompt:
                issues.append(Issue(
                    id=f"STYLE-{loc.get('location_id', '')}",
                    severity=IssueSeverity.MAJOR,
                    location=f"location: {loc.get('name', '')}",
                    category="style_uniformity",
                    description=f"场景 {loc.get('name')} 的提示词模板未包含风格声明",
                    evidence=f"prompt中缺少 '{art_style}'",
                    suggestion=f"在 prompt_template 末尾添加 '{art_style} art style'",
                ))

        return issues

    def _check_character_differentiation(self, characters: list) -> list[Issue]:
        """Check that any two characters are visually distinguishable."""
        issues = []
        for i in range(len(characters)):
            for j in range(i + 1, len(characters)):
                a = characters[i]
                b = characters[j]

                # Compare key distinguishing dimensions
                same_hair = (
                    a["design_sheet"]["appearance"]["hair"]["color"] ==
                    b["design_sheet"]["appearance"]["hair"]["color"]
                )
                same_face = (
                    a["design_sheet"]["appearance"]["face"]["shape"] ==
                    b["design_sheet"]["appearance"]["face"]["shape"]
                )
                same_body = (
                    a["design_sheet"]["appearance"]["body_type"] ==
                    b["design_sheet"]["appearance"]["body_type"]
                )

                # If all 3 match, characters are too similar
                similarity_score = sum([same_hair, same_face, same_body])
                if similarity_score >= 3:
                    issues.append(Issue(
                        id=f"DIFF-{a['character_id']}-{b['character_id']}",
                        severity=IssueSeverity.BLOCKER,
                        location=f"characters: {a['ref_name']} vs {b['ref_name']}",
                        category="character_differentiation",
                        description=f"角色 {a['ref_name']} 和 {b['ref_name']} 视觉辨识度严重不足",
                        evidence=f"外貌维度重复: hair={same_hair}, face={same_face}, body={same_body}",
                        suggested_fix_example=f"调整其中一位的识别特征: 改变发型颜色、增加疤痕/胎记、调整体型差异、或添加独特配饰",
                    ))
                elif similarity_score >= 2:
                    issues.append(Issue(
                        id=f"DIFF-{a['character_id']}-{b['character_id']}",
                        severity=IssueSeverity.MAJOR,
                        location=f"characters: {a['ref_name']} vs {b['ref_name']}",
                        category="character_differentiation",
                        description=f"角色 {a['ref_name']} 和 {b['ref_name']} 外貌相似度较高",
                        evidence=f"外貌维度重复: hair={same_hair}, face={same_face}, body={same_body}",
                        suggestion="建议增加差异化特征",
                    ))

        return issues

    def _check_scale_proportion(
        self, characters: list, locations: list, props: list
    ) -> list[Issue]:
        """Check relative scales are reasonable."""
        issues = []
        # Check character heights relative to each other
        heights = {
            c["ref_name"]: c["design_sheet"]["appearance"].get("height_cm", 170)
            for c in characters
        }
        if heights:
            max_h = max(heights.values())
            min_h = min(heights.values())
            if max_h > min_h * 2.5:
                issues.append(Issue(
                    id="SCALE-height",
                    severity=IssueSeverity.MINOR,
                    location="characters",
                    category="scale_proportion",
                    description=f"角色身高差异过大 (最高{max_h}cm vs 最矮{min_h}cm)",
                    evidence=f"身高范围: {min_h}-{max_h}cm",
                ))

        return issues

    def _check_color_harmony(
        self, characters: list, locations: list, style_manifest: dict
    ) -> list[Issue]:
        """Check colors stay within the defined palette and don't clash with scene backgrounds."""
        issues = []
        primary_colors = set(
            style_manifest.get("color_palette", {}).get("primary_colors", [])
        )

        for char in characters:
            for costume in char["design_sheet"].get("costumes", []):
                for color in costume.get("color_palette", []):
                    if color not in primary_colors and primary_colors:
                        issues.append(Issue(
                            id=f"COLOR-{char['character_id']}-{costume['costume_id']}",
                            severity=IssueSeverity.MINOR,
                            location=f"character: {char['ref_name']}, costume: {costume['name']}",
                            category="color_harmony",
                            description=f"服装颜色 {color} 不在全局主色调中",
                            suggestion=f"考虑替换为色板内的颜色: {primary_colors}",
                        ))

        return issues

    def _check_asset_coverage(
        self, characters: list, locations: list, props: list, script: dict
    ) -> list[Issue]:
        """CROSS-S1-001~003: Check all script entities have asset designs."""
        issues = []

        # Check character coverage
        script_chars = {
            c.get("ref_name") for c in script.get("character_index", {}).get("characters", [])
        }
        asset_chars = {c.get("ref_name") for c in characters}
        missing_chars = script_chars - asset_chars
        for name in missing_chars:
            issues.append(Issue(
                id=f"COVER-CHAR-{name}",
                severity=IssueSeverity.BLOCKER,
                location=f"character: {name}",
                category="character_coverage",
                description=f"角色 '{name}' 在剧本中出现但缺少资产设计稿",
                evidence="character_index 中存在但 characters 中缺失",
            ))

        # Check location coverage
        script_locs = {
            loc.get("name") for loc in script.get("location_index", {}).get("locations", [])
        }
        asset_locs = {loc.get("name") for loc in locations}
        missing_locs = script_locs - asset_locs
        for name in missing_locs:
            issues.append(Issue(
                id=f"COVER-LOC-{name}",
                severity=IssueSeverity.BLOCKER,
                location=f"location: {name}",
                category="location_coverage",
                description=f"场景 '{name}' 在剧本中出现但缺少资产设计稿",
                evidence="location_index 中存在但 locations 中缺失",
            ))

        return issues

    # ── Round 2 Checks ──

    def _check_costume_face_consistency(self, characters: list) -> list[Issue]:
        """Check that the same character's face remains consistent across costumes."""
        issues = []
        for char in characters:
            if len(char["design_sheet"]["costumes"]) > 1:
                # Verify all costumes share the same face description
                # This is enforced by design (face is defined once per character),
                # but we flag if costume descriptions inadvertently override facial features
                for costume in char["design_sheet"]["costumes"]:
                    desc = costume.get("description", "")
                    face_terms = ["脸", "眼睛", "鼻子", "嘴", "face", "eye", "nose", "mouth"]
                    if any(term in desc.lower() for term in face_terms):
                        issues.append(Issue(
                            id=f"COSTFACE-{char['character_id']}-{costume['costume_id']}",
                            severity=IssueSeverity.MINOR,
                            location=f"character: {char['ref_name']}, costume: {costume['name']}",
                            category="costume_face_consistency",
                            description=f"服装描述中包含了面部特征描述，可能导致角色面部不一致",
                            suggestion="将面部描述从服装描述中移除，面部特征由 character.appearance.face 统一管理",
                        ))
        return issues

    def _check_prompt_compatibility(
        self, characters: list, locations: list, style_manifest: dict
    ) -> list[Issue]:
        """Check that prompts from different assets can be concatenated without style drift."""
        issues = []
        negative_prompt = style_manifest.get("global_negative_prompt", "")

        # Verify all character prompts contain the global negative prompt
        for char in characters:
            prompt = char.get("character_prompt_template", "")
            if negative_prompt and negative_prompt not in prompt:
                issues.append(Issue(
                    id=f"PROMPT-{char['character_id']}",
                    severity=IssueSeverity.MAJOR,
                    location=f"character: {char['ref_name']}",
                    category="cross_asset_prompt_compatibility",
                    description=f"角色提示词缺少全局负向提示词约束",
                    suggestion=f"自动注入: {negative_prompt[:100]}...",
                ))

        return issues

    # ── Scoring ──

    def _score_coverage(self, characters, locations, props, script) -> int:
        script_char_count = len(script.get("character_index", {}).get("characters", []))
        script_loc_count = len(script.get("location_index", {}).get("locations", []))
        if script_char_count == 0 and script_loc_count == 0:
            return 80
        char_cov = len(characters) / max(script_char_count, 1)
        loc_cov = len(locations) / max(script_loc_count, 1)
        return round(min(char_cov, loc_cov) * 100)

    def _score_consistency(self, issues: list) -> int:
        base = 95
        base -= len([i for i in issues if i.severity == IssueSeverity.BLOCKER]) * 15
        base -= len([i for i in issues if i.severity == IssueSeverity.MAJOR]) * 5
        return max(base, 0)

    def _score_design_quality(self, characters, locations) -> int:
        return 75  # Placeholder — would use LLM evaluation

    def _score_prompt_quality(self, characters, locations) -> int:
        total = len(characters) + len(locations)
        if total == 0:
            return 70
        has_prompts = sum(1 for c in characters if c.get("character_prompt_template")) + \
                      sum(1 for l in locations if l.get("location_prompt_template"))
        return round((has_prompts / total) * 100)

    def _score_style_compliance(self, style_manifest) -> int:
        return 90 if style_manifest else 50

    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        raise NotImplementedError("Reviewer agents cannot revise — only review")
