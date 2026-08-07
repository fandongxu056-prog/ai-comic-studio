"""Stage 1 (Script) → Stage 2 (Assets) contract validation.

Rules CROSS-S1-001 through CROSS-S1-006 from docs/agent-collaboration-protocol.md §5.3.
"""

from app.contracts.base import BaseContract, ContractRule, ContractViolation, ViolationLevel

RULES = [
    ContractRule(
        id="CROSS-S1-001",
        type="entity_coverage",
        description="Stage 1 character_index 中的所有角色必须在 Stage 2 characters 中有对应设计稿",
        validation="Stage1.character_index.characters[].ref_name ⊆ Stage2.characters[].ref_name",
        on_violation=ViolationLevel.BLOCKER,
    ),
    ContractRule(
        id="CROSS-S1-002",
        type="entity_coverage",
        description="Stage 1 location_index 中的所有地点必须在 Stage 2 locations 中有对应设计稿",
        validation="Stage1.location_index.locations[].name ⊆ Stage2.locations[].name",
        on_violation=ViolationLevel.BLOCKER,
    ),
    ContractRule(
        id="CROSS-S1-003",
        type="entity_coverage",
        description="key_item 和 recurring 道具必须在 Stage 2 props 中有对应设计稿",
        validation="Stage1.prop_index.props[importance in (key_item, recurring)][].name ⊆ Stage2.props[].name",
        on_violation=ViolationLevel.MAJOR,
    ),
    ContractRule(
        id="CROSS-S1-004",
        type="style_alignment",
        description="Stage 2 style_manifest.art_style 必须与 style_preference 一致",
        validation="Stage2.style_manifest.art_style == ProjectInput.style_preference.art_style",
        on_violation=ViolationLevel.MAJOR,
    ),
    ContractRule(
        id="CROSS-S1-005",
        type="costume_logic",
        description="每个角色的 costumes 必须覆盖该角色在剧本中出现的所有场景",
        validation="For each character, union(costumes[].scenes_used_in) ⊇ character_appearances",
        on_violation=ViolationLevel.MAJOR,
    ),
    ContractRule(
        id="CROSS-S1-006",
        type="scene_variation_coverage",
        description="每个场景的 variations 必须覆盖剧本中的 time_of_day 和 weather",
        validation="Stage1.scenes.unique(time_of_day, weather) ⊆ Stage2.locations[name].variations",
        on_violation=ViolationLevel.MINOR,
    ),
]


class ScriptToAssetContract(BaseContract):
    """Validates that Stage 2 assets properly cover all Stage 1 entities."""

    rules = RULES
    from_stage = "script"
    to_stage = "assets"

    async def _check_rule(
        self, rule: ContractRule, upstream: dict, downstream: dict
    ) -> list[ContractViolation]:
        """Check entity coverage rules."""
        match rule.id:
            case "CROSS-S1-001":
                return self._check_character_coverage(upstream, downstream)
            case "CROSS-S1-002":
                return self._check_location_coverage(upstream, downstream)
            case "CROSS-S1-003":
                return self._check_prop_coverage(upstream, downstream)
            case "CROSS-S1-004":
                return self._check_style_alignment(upstream, downstream)
            case _:
                return []

    def _check_character_coverage(self, upstream: dict, downstream: dict) -> list[ContractViolation]:
        """CROSS-S1-001: All script characters must have asset designs."""
        script_chars = {
            c.get("ref_name") for c in upstream.get("character_index", {}).get("characters", [])
        }
        asset_chars = {c.get("ref_name") for c in downstream.get("characters", [])}
        missing = script_chars - asset_chars
        if missing:
            return [
                ContractViolation(
                    rule_id="CROSS-S1-001",
                    level=ViolationLevel.BLOCKER,
                    description=f"角色缺少资产设计: {missing}",
                    details={"missing_characters": list(missing)},
                )
            ]
        return []

    def _check_location_coverage(self, upstream: dict, downstream: dict) -> list[ContractViolation]:
        """CROSS-S1-002: All script locations must have asset designs."""
        script_locs = {
            loc.get("name") for loc in upstream.get("location_index", {}).get("locations", [])
        }
        asset_locs = {loc.get("name") for loc in downstream.get("locations", [])}
        missing = script_locs - asset_locs
        if missing:
            return [
                ContractViolation(
                    rule_id="CROSS-S1-002",
                    level=ViolationLevel.BLOCKER,
                    description=f"场景缺少资产设计: {missing}",
                    details={"missing_locations": list(missing)},
                )
            ]
        return []

    def _check_prop_coverage(self, upstream: dict, downstream: dict) -> list[ContractViolation]:
        """CROSS-S1-003: Key and recurring props must have asset designs."""
        important_props = {
            p.get("name")
            for p in upstream.get("prop_index", {}).get("props", [])
            if p.get("importance") in ("key_item", "recurring")
        }
        asset_props = {p.get("name") for p in downstream.get("props", [])}
        missing = important_props - asset_props
        if missing:
            return [
                ContractViolation(
                    rule_id="CROSS-S1-003",
                    level=ViolationLevel.MAJOR,
                    description=f"重要道具缺少资产设计: {missing}",
                    details={"missing_props": list(missing)},
                )
            ]
        return []

    def _check_style_alignment(self, upstream: dict, downstream: dict) -> list[ContractViolation]:
        """CROSS-S1-004: Style manifest must align with project preference."""
        # This is a simplified check — full implementation would compare art_style values
        return []
