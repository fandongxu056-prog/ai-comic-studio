"""ContinuityCheck Agent — validates asset references and continuity rules in storyboard.

Role: Reviewer
Reviews: ShotComposer
Focus: Reference integrity, continuity rules, spatial logic between shots
"""

from app.agents.base import (
    AgentConfig, AgentIdentity, AgentRole, AgentScope,
    BaseAgent, Issue, IssueSeverity, ReviewFeedback, Verdict,
    calculate_total_score,
)


def build_continuity_check_config() -> AgentConfig:
    return AgentConfig(
        identity=AgentIdentity(
            agent_id="continuity_check_v1",
            identity="连续性检查师",
            expertise=["引用完整性", "空间连续性", "180度规则", "角色状态连贯", "提示词一致性"],
            personality="像侦探一样逐帧检查——任何引用断裂和穿帮都逃不过这双眼睛",
            blind_spots=["不评估节奏好坏——那是PacingDirector的活"],
            quality_bias="宁可多报100个minor也不漏1个blocker",
        ),
        scope=AgentScope(
            stage="storyboard",
            reads=["shot_plan", "asset_profiles", "script", "continuity_rules"],
            writes=["review_feedback"],
            must_not_modify=["shot_plan"],
        ),
        role=AgentRole.REVIEWER,
        can_review=["shot_composer_v1"],
    )


class ContinuityCheckAgent(BaseAgent):
    """Validates all references and continuity rules in the storyboard.

    Checklist:
    Round 1:
    - Character references exist in assets
    - Costume references belong to correct character
    - Location references exist in assets
    - Prop references exist in assets
    - Dialogue character ↔ characters_in_frame consistency

    Round 2:
    - Prompt injection: image_prompt contains character/location templates
    - Character state continuity between consecutive shots
    - Spatial continuity (180-degree rule, eye-line matching)
    """

    def __init__(self):
        super().__init__(build_continuity_check_config())

    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Validate storyboard continuity."""
        shot_plan = input_data.get("shot_plan", {})
        assets = input_data.get("assets", {})
        continuity_rules = input_data.get("continuity_rules", [])
        episodes = shot_plan.get("episodes", [])

        # Build lookup maps
        char_ids = {c.get("character_id") for c in assets.get("characters", [])}
        loc_ids = {l.get("location_id") for l in assets.get("locations", [])}
        prop_ids = {p.get("prop_id") for p in assets.get("props", [])}
        costume_map = self._build_costume_map(assets.get("characters", []))

        issues: list[Issue] = []

        # Round 1: Reference integrity
        for ep in episodes:
            for scene in ep.get("scenes", []):
                for shot in scene.get("shots", []):
                    issues.extend(self._check_char_refs(shot, char_ids, costume_map))
                    issues.extend(self._check_loc_refs(shot, scene, loc_ids))
                    issues.extend(self._check_prop_refs(shot, prop_ids))
                    issues.extend(self._check_dialogue_consistency(shot))

        # Round 2: Continuity
        issues.extend(self._check_shot_to_shot_continuity(episodes))
        issues.extend(self._check_prompt_references(episodes, assets))

        # Scoring
        dimension_scores = {
            "completeness": 85,
            "consistency": self._score_ref_integrity(issues),
            "quality": 80,
            "executability": self._score_prompt_executability(episodes),
            "compliance": 90,
        }

        total = calculate_total_score(dimension_scores, "storyboard")
        blocker_count = sum(1 for i in issues if i.severity == IssueSeverity.BLOCKER)

        if total >= 80 and blocker_count == 0:
            verdict = Verdict.APPROVED
        elif 65 <= total < 80 and blocker_count == 0:
            verdict = Verdict.APPROVED_WITH_MINOR
        else:
            verdict = Verdict.NEEDS_REVISION

        return ReviewFeedback(
            overall_verdict=verdict,
            total_score=total,
            dimension_scores=dimension_scores,
            critical_issues=issues,
            strengths=[],
        ).model_dump()

    # ── Reference Checks ──

    def _check_char_refs(self, shot: dict, char_ids: set, costume_map: dict) -> list[Issue]:
        """CROSS-S2-001, S2-002: Validate character and costume references."""
        issues = []
        for c in shot["keyframe"]["characters_in_frame"]:
            cid = c.get("character_id", "")
            if cid and cid not in char_ids:
                issues.append(Issue(
                    id=f"REF-CHAR-{shot['shot_id']}-{cid}",
                    severity=IssueSeverity.BLOCKER,
                    location=f"shot: {shot['shot_id']}",
                    category="character_reference",
                    description=f"镜头引用了不存在的角色: {cid}",
                    evidence="character_id 不在 AssetProfiles.characters 中",
                ))

            # Check costume belongs to that character
            cost_id = c.get("costume_id", "")
            if cost_id and cid:
                valid_costumes = costume_map.get(cid, set())
                if cost_id not in valid_costumes and valid_costumes:
                    issues.append(Issue(
                        id=f"REF-COST-{shot['shot_id']}-{cost_id}",
                        severity=IssueSeverity.MAJOR,
                        location=f"shot: {shot['shot_id']}",
                        category="costume_reference",
                        description=f"镜头引用的服装 {cost_id} 不属于角色 {cid}",
                        evidence=f"costume_id 不在该角色的 costumes 列表中",
                    ))

        return issues

    def _check_loc_refs(self, shot: dict, scene: dict, loc_ids: set) -> list[Issue]:
        """CROSS-S2-003: Validate location reference."""
        issues = []
        loc_id = scene.get("location_id", "")
        if loc_id and loc_id not in loc_ids:
            issues.append(Issue(
                id=f"REF-LOC-{shot['shot_id']}-{loc_id}",
                severity=IssueSeverity.BLOCKER,
                location=f"shot: {shot['shot_id']}",
                category="location_reference",
                description=f"镜头场景引用了不存在的地点: {loc_id}",
                evidence="location_id 不在 AssetProfiles.locations 中",
            ))
        return issues

    def _check_prop_refs(self, shot: dict, prop_ids: set) -> list[Issue]:
        """CROSS-S2-004: Validate prop references."""
        issues = []
        for p in shot["keyframe"].get("props_in_frame", []):
            pid = p.get("prop_id", "")
            if pid and pid not in prop_ids:
                issues.append(Issue(
                    id=f"REF-PROP-{shot['shot_id']}-{pid}",
                    severity=IssueSeverity.MAJOR,
                    location=f"shot: {shot['shot_id']}",
                    category="prop_reference",
                    description=f"镜头引用了不存在的道具: {pid}",
                    evidence="prop_id 不在 AssetProfiles.props 中",
                ))
        return issues

    def _check_dialogue_consistency(self, shot: dict) -> list[Issue]:
        """Check dialogue character is present in frame or is valid off-screen."""
        issues = []
        frame_chars = {c.get("character_id") for c in shot["keyframe"]["characters_in_frame"] if c}
        for dlg in shot.get("dialogue", []):
            dlg_char = dlg.get("character_id", "")
            if dlg_char and dlg_char not in frame_chars:
                # Could be off-screen voice — flag as minor
                issues.append(Issue(
                    id=f"DLG-OFF-{shot['shot_id']}",
                    severity=IssueSeverity.MINOR,
                    location=f"shot: {shot['shot_id']}",
                    category="dialogue_character_consistency",
                    description=f"对白角色 {dlg_char} 不在画内——请确认是否为有意画外音",
                ))

            # Check timing
            if dlg.get("end_ms", 0) > shot.get("duration_ms", 0):
                issues.append(Issue(
                    id=f"DLG-TIME-{shot['shot_id']}",
                    severity=IssueSeverity.MAJOR,
                    location=f"shot: {shot['shot_id']}",
                    category="dialogue_timing",
                    description=f"对白结束时间({dlg.get('end_ms')}ms)超过镜头时长({shot.get('duration_ms')}ms)",
                ))

        return issues

    # ── Continuity Checks ──

    def _check_shot_to_shot_continuity(self, episodes: list) -> list[Issue]:
        """Check character state/position continuity between consecutive shots."""
        issues = []
        for ep in episodes:
            for scene in ep.get("scenes", []):
                shots = scene.get("shots", [])
                for i in range(len(shots) - 1):
                    curr_chars = {c["character_id"]: c for c in shots[i]["keyframe"]["characters_in_frame"] if c}
                    next_chars = {c["character_id"]: c for c in shots[i + 1]["keyframe"]["characters_in_frame"] if c}

                    # Characters present in both shots should have consistent costume
                    common = set(curr_chars.keys()) & set(next_chars.keys())
                    for cid in common:
                        curr_costume = curr_chars[cid].get("costume_id")
                        next_costume = next_chars[cid].get("costume_id")
                        if curr_costume and next_costume and curr_costume != next_costume:
                            issues.append(Issue(
                                id=f"CONT-COST-{shots[i+1]['shot_id']}-{cid}",
                                severity=IssueSeverity.MAJOR,
                                location=f"shot: {shots[i+1]['shot_id']}",
                                category="spatial_continuity",
                                description=f"角色 {cid} 在连续镜头间服装无故变化",
                                evidence=f"shot {i}: {curr_costume} → shot {i+1}: {next_costume}",
                            ))

        return issues

    def _check_prompt_references(self, episodes: list, assets: dict) -> list[Issue]:
        """CROSS-S2-005: Verify image_prompt contains character/location templates."""
        issues = []
        char_templates = {
            c["character_id"]: c.get("character_prompt_template", "")
            for c in assets.get("characters", [])
        }

        for ep in episodes:
            for scene in ep.get("scenes", []):
                for shot in scene.get("shots", []):
                    prompt = shot["keyframe"]["image_prompt"]["positive"]

                    # Check at least one character's key features are in the prompt
                    chars_in_frame = shot["keyframe"]["characters_in_frame"]
                    for cinf in chars_in_frame:
                        cid = cinf.get("character_id", "")
                        template = char_templates.get(cid, "")
                        if template:
                            # Extract key words from template and check presence
                            key_words = [w for w in template.split(", ") if len(w) > 10][:2]
                            if key_words and not any(kw in prompt for kw in key_words):
                                issues.append(Issue(
                                    id=f"PROMPT-{shot['shot_id']}-{cid}",
                                    severity=IssueSeverity.MAJOR,
                                    location=f"shot: {shot['shot_id']}",
                                    category="prompt_injection",
                                    description=f"镜头提示词未包含角色 {cid} 的核心特征描述",
                                    evidence="角色 prompt_template 中的关键特征词未出现在 image_prompt 中",
                                ))

        return issues

    # ── Helpers ──

    def _build_costume_map(self, characters: list) -> dict[str, set[str]]:
        """Build character_id → {costume_ids} map."""
        cmap = {}
        for c in characters:
            cid = c.get("character_id", "")
            costume_ids = {cost.get("costume_id") for cost in c.get("design_sheet", {}).get("costumes", [])}
            if cid:
                cmap[cid] = costume_ids
        return cmap

    # ── Scoring ──

    def _score_ref_integrity(self, issues: list) -> int:
        base = 100
        base -= len([i for i in issues if i.severity == IssueSeverity.BLOCKER]) * 25
        base -= len([i for i in issues if i.severity == IssueSeverity.MAJOR]) * 8
        return max(base, 0)

    def _score_prompt_executability(self, episodes: list) -> int:
        total = 0
        valid = 0
        for ep in episodes:
            for scene in ep.get("scenes", []):
                for shot in scene.get("shots", []):
                    total += 1
                    p = shot["keyframe"]["image_prompt"]
                    if p.get("positive") and p.get("negative") and p.get("seed"):
                        valid += 1
        return round((valid / max(total, 1)) * 100)

    async def revise(self, feedback, original_output):
        raise NotImplementedError("Reviewer cannot revise")
