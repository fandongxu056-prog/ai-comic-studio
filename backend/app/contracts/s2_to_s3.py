"""Stage 2 (Assets) → Stage 3 (Storyboard) contract validation.

Rules CROSS-S2-001 through CROSS-S2-006 from docs/agent-collaboration-protocol.md §5.4.
"""

from app.contracts.base import BaseContract, ContractRule, ContractViolation, ViolationLevel

RULES = [
    ContractRule(
        id="CROSS-S2-001", type="character_reference",
        description="每个 shot 的 character_id 必须存在于 Stage 2 characters",
        validation="∀ shot: characters_in_frame[].character_id ⊆ Stage2.characters[].character_id",
        on_violation=ViolationLevel.BLOCKER,
    ),
    ContractRule(
        id="CROSS-S2-002", type="costume_reference",
        description="costume_id 必须属于对应角色在 Stage 2 中定义的服装",
        validation="costume_id ∈ Stage2.characters[character_id].costumes[].costume_id",
        on_violation=ViolationLevel.MAJOR,
    ),
    ContractRule(
        id="CROSS-S2-003", type="location_reference",
        description="location_id 必须存在于 Stage 2 locations",
        validation="∀ shot: location_id ∈ Stage2.locations[].location_id",
        on_violation=ViolationLevel.BLOCKER,
    ),
    ContractRule(
        id="CROSS-S2-004", type="prop_reference",
        description="props_in_frame 中的 prop_id 必须存在于 Stage 2 props",
        validation="∀ shot: prop_id ⊆ Stage2.props[].prop_id",
        on_violation=ViolationLevel.MAJOR,
    ),
    ContractRule(
        id="CROSS-S2-005", type="prompt_injection",
        description="image_prompt 必须包含角色和场景的 prompt template",
        validation="prompt 字符串中包含角色/场景的核心特征词",
        on_violation=ViolationLevel.BLOCKER,
    ),
    ContractRule(
        id="CROSS-S2-006", type="style_seed_continuity",
        description="同 episode 内所有 shot seed 必须基于 global_seed 确定性偏移",
        validation="seed == global_seed + shot_index * prime_offset",
        on_violation=ViolationLevel.MAJOR,
    ),
]


class AssetToStoryboardContract(BaseContract):
    """Validates Stage 3 storyboard properly references Stage 2 assets."""
    rules = RULES
    from_stage = "assets"
    to_stage = "storyboard"
