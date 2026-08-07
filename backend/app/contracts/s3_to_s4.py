"""Stage 3 (Storyboard) → Stage 4 (Production) contract validation.

Rules CROSS-S3-001 through CROSS-S3-004 from docs/agent-collaboration-protocol.md §5.5.
"""

from app.contracts.base import BaseContract, ContractRule, ContractViolation, ViolationLevel

RULES = [
    ContractRule(
        id="CROSS-S3-001", type="prompt_completeness",
        description="每个 shot 必须有完整的 image_prompt (positive + negative + seed + model_params)",
        validation="∀ shot: image_prompt 所有 required 字段不为空",
        on_violation=ViolationLevel.BLOCKER,
    ),
    ContractRule(
        id="CROSS-S3-002", type="dialogue_timing",
        description="dialogue[].end_ms ≤ shot.duration_ms",
        validation="∀ shot: dialogue.end_ms <= shot.duration_ms",
        on_violation=ViolationLevel.MAJOR,
    ),
    ContractRule(
        id="CROSS-S3-003", type="episode_duration",
        description="每集总 duration_ms 必须在 target 的 ±15% 范围内",
        validation="|episode_duration - target| / target ≤ 0.15",
        on_violation=ViolationLevel.MAJOR,
    ),
    ContractRule(
        id="CROSS-S3-004", type="asset_urls",
        description="所有 reference image URLs 必须有效",
        validation="HTTP HEAD 检查所有 reference_images URL",
        on_violation=ViolationLevel.BLOCKER,
    ),
]


class StoryboardToProductionContract(BaseContract):
    """Validates Stage 4 production inputs from Stage 3 storyboard."""
    rules = RULES
    from_stage = "storyboard"
    to_stage = "production"
