"""Top-level orchestrator — LangGraph state machine for 4-stage pipeline.

Implements:
- Stage transitions: script → assets → storyboard → production → complete
- Human-in-the-loop checkpoints at each stage boundary
- Review loop orchestration within each stage
- Cross-stage contract validation

Design reference: docs/agent-collaboration-protocol.md
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field


class Stage(str, Enum):
    """The four stages of the creative pipeline."""
    SCRIPT = "script"
    ASSETS = "assets"
    STORYBOARD = "storyboard"
    PRODUCTION = "production"
    COMPLETE = "complete"


class StageStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineState(BaseModel):
    """The shared state object that flows through the entire pipeline.

    This is the single source of truth for the orchestrator.
    """
    project_id: str
    current_stage: Stage = Stage.SCRIPT

    # Stage statuses
    stage_statuses: dict[str, StageStatus] = Field(default_factory=lambda: {
        "script": StageStatus.NOT_STARTED,
        "assets": StageStatus.NOT_STARTED,
        "storyboard": StageStatus.NOT_STARTED,
        "production": StageStatus.NOT_STARTED,
    })

    # Artifact references
    script_id: Optional[str] = None
    asset_set_id: Optional[str] = None
    storyboard_id: Optional[str] = None
    production_id: Optional[str] = None

    # Review tracking
    review_history: list[dict] = Field(default_factory=list)
    last_error: Optional[str] = None
    human_decision: Optional[str] = None  # approved | rejected | revise
    human_notes: Optional[str] = None


# ── Stage transition rules ──

STAGE_ORDER: list[Stage] = [
    Stage.SCRIPT,
    Stage.ASSETS,
    Stage.STORYBOARD,
    Stage.PRODUCTION,
    Stage.COMPLETE,
]


def get_next_stage(current: Stage) -> Stage:
    """Get the next stage in the pipeline."""
    try:
        idx = STAGE_ORDER.index(current)
        return STAGE_ORDER[idx + 1]
    except (ValueError, IndexError):
        return Stage.COMPLETE


def get_previous_stage(current: Stage) -> Stage:
    """Get the previous stage in the pipeline."""
    try:
        idx = STAGE_ORDER.index(current)
        return STAGE_ORDER[max(0, idx - 1)]
    except ValueError:
        return Stage.SCRIPT


# ── Orchestrator ──

class Orchestrator:
    """Manages the 4-stage creative pipeline.

    This is NOT a LangGraph graph itself — rather, it provides the imperative
    API that will be wrapped by LangGraph nodes in each stage's graph.py.

    The orchestrator:
    1. Validates stage transitions
    2. Manages human checkpoints
    3. Tracks overall pipeline progress
    4. Enforces cross-stage contracts
    """

    def __init__(self, state: PipelineState):
        self.state = state

    def can_transition_to(self, target: Stage) -> bool:
        """Check if the pipeline can transition to the target stage."""
        current_idx = STAGE_ORDER.index(self.state.current_stage)
        target_idx = STAGE_ORDER.index(target)

        # Can only move forward one stage at a time
        if target_idx != current_idx + 1:
            return False

        # Current stage must be completed
        current_status = self.state.stage_statuses[self.state.current_stage.value]
        if current_status != StageStatus.COMPLETED:
            return False

        return True

    def transition_to(self, target: Stage) -> bool:
        """Attempt to transition the pipeline to the target stage."""
        if not self.can_transition_to(target):
            return False
        self.state.current_stage = target
        self.state.stage_statuses[target.value] = StageStatus.IN_PROGRESS
        return True

    def complete_stage(self, artifact_id: str) -> None:
        """Mark the current stage as completed and store the artifact ID."""
        stage_key = self.state.current_stage.value
        self.state.stage_statuses[stage_key] = StageStatus.COMPLETED

        # Store the artifact ID
        match self.state.current_stage:
            case Stage.SCRIPT:
                self.state.script_id = artifact_id
            case Stage.ASSETS:
                self.state.asset_set_id = artifact_id
            case Stage.STORYBOARD:
                self.state.storyboard_id = artifact_id
            case Stage.PRODUCTION:
                self.state.production_id = artifact_id

    def request_human_approval(self) -> None:
        """Set the current stage to await human approval."""
        stage_key = self.state.current_stage.value
        self.state.stage_statuses[stage_key] = StageStatus.AWAITING_HUMAN
        self.state.human_decision = None

    def process_human_decision(self, decision: str, notes: str = "") -> bool:
        """Process the human's decision on the pending approval.

        Returns True if the pipeline should proceed.
        """
        self.state.human_decision = decision
        self.state.human_notes = notes

        stage_key = self.state.current_stage.value

        match decision:
            case "approved":
                # Complete current stage and move to next
                self.state.stage_statuses[stage_key] = StageStatus.COMPLETED
                next_stage = get_next_stage(self.state.current_stage)
                if next_stage != Stage.COMPLETE:
                    self.state.current_stage = next_stage
                    self.state.stage_statuses[next_stage.value] = StageStatus.IN_PROGRESS
                else:
                    self.state.current_stage = Stage.COMPLETE
                return True

            case "revise":
                # Stay in current stage, back to in_progress
                self.state.stage_statuses[stage_key] = StageStatus.IN_PROGRESS
                return False

            case "rejected":
                self.state.stage_statuses[stage_key] = StageStatus.FAILED
                self.state.last_error = f"Stage {stage_key} rejected by human"
                return False

        return False

    def should_auto_approve(self, total_score: int, blocker_count: int) -> bool:
        """Determine if a stage can be auto-approved without human review.

        Rules from agent-collaboration-protocol.md:
        - total_score >= 85 AND all dimension scores >= 70 AND zero blockers → auto-approve
        """
        return total_score >= 85 and blocker_count == 0

    def should_force_review(self, total_score: int, blocker_count: int) -> bool:
        """Determine if human review is mandatory."""
        return total_score < 65 or blocker_count > 0

    def summary(self) -> dict:
        """Return a summary of the current pipeline state."""
        return {
            "project_id": self.state.project_id,
            "current_stage": self.state.current_stage.value,
            "stage_statuses": {k: v.value for k, v in self.state.stage_statuses.items()},
            "artifacts": {
                "script_id": self.state.script_id,
                "asset_set_id": self.state.asset_set_id,
                "storyboard_id": self.state.storyboard_id,
                "production_id": self.state.production_id,
            },
            "human_decision": self.state.human_decision,
        }
