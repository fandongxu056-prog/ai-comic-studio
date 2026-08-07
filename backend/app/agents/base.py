"""Base agent class and communication protocol.

Implements the agent role 5-tuple and structured message format
defined in docs/agent-collaboration-protocol.md.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.utils.id_generator import generate_message_id


# ── Agent Identity ──

class AgentIdentity(BaseModel):
    """Agent 5-tuple identity definition."""
    agent_id: str
    identity: str  # e.g., "资深漫剧编剧"
    expertise: list[str] = Field(default_factory=list)
    personality: str = ""
    blind_spots: list[str] = Field(default_factory=list)
    quality_bias: str = ""


class AgentScope(BaseModel):
    """What the agent can read and write."""
    stage: str  # script | assets | storyboard | production
    reads: list[str] = Field(default_factory=list)
    writes: list[str] = Field(default_factory=list)
    must_not_modify: list[str] = Field(default_factory=list)


class AgentRole(str, Enum):
    AUTHOR = "author"
    REVIEWER = "reviewer"


class AgentConfig(BaseModel):
    """Full agent configuration."""
    identity: AgentIdentity
    scope: AgentScope
    role: AgentRole
    can_be_reviewed_by: list[str] = Field(default_factory=list)
    can_review: list[str] = Field(default_factory=list)


# ── Review Verdicts ──

class Verdict(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_MINOR = "approved_with_minor"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"


# ── Issue ──

class IssueSeverity(str, Enum):
    BLOCKER = "blocker"
    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"


class Issue(BaseModel):
    """A single quality issue found during review."""
    id: str
    severity: IssueSeverity
    location: str  # e.g., "episode=3, scene=2, segment=5"
    category: str  # e.g., "conflict_density", "dialogue_naturalness"
    description: str
    evidence: str
    suggestion: str = ""
    suggested_fix_example: str = ""


class ReviewFeedback(BaseModel):
    """Structured review feedback from a reviewer agent."""
    overall_verdict: Verdict
    total_score: int = Field(ge=0, le=100)
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    critical_issues: list[Issue] = Field(default_factory=list)
    strengths: list[dict] = Field(default_factory=list)
    continuity_flags: list[dict] = Field(default_factory=list)


# ── Agent Message ──

class AgentMessage(BaseModel):
    """Structured message between agents.

    All inter-agent communication uses this format — no free-text chat.
    """
    message_id: str = Field(default_factory=generate_message_id)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sender: dict = Field(default_factory=dict)  # {agent_id, role}
    recipient: dict = Field(default_factory=dict)  # {agent_id, role}
    message_type: str = "review_feedback"
    target_artifact: dict = Field(default_factory=dict)  # {artifact_type, artifact_ref, version}
    content: ReviewFeedback | None = None
    iteration_round: int = 1
    ttl_rounds_remaining: int = 3
    reply_to: str | None = None


# ── Review History ──

class ReviewRecord(BaseModel):
    """A single review round record."""
    round: int
    timestamp: str
    reviewer: dict  # {agent_id, agent_version}
    verdict: Verdict
    total_score: int
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    issues: list[dict] = Field(default_factory=list)
    revision_delta: dict | None = None


# ── Base Agent ──

class BaseAgent(ABC):
    """Abstract base class for all agents in the platform.

    Each agent has:
    - A config defining its identity, scope, and role
    - A review_history tracking all review rounds
    - Abstract methods for its core behaviors
    """

    config: AgentConfig
    review_history: list[ReviewRecord] = []

    def __init__(self, config: AgentConfig):
        self.config = config
        self.review_history = []

    @property
    def agent_id(self) -> str:
        return self.config.identity.agent_id

    @property
    def role(self) -> AgentRole:
        return self.config.role

    @abstractmethod
    async def execute(self, input_data: dict, context: dict | None = None) -> dict:
        """Execute the agent's primary task (author) or review (reviewer).

        Args:
            input_data: The artifact or context to work with.
            context: Optional additional context (project settings, style prefs, etc.).

        Returns:
            For Author agents: the created artifact (structured_script, asset_profiles, shot_plan).
            For Reviewer agents: a ReviewFeedback object serialized as dict.
        """
        ...

    @abstractmethod
    async def revise(self, feedback: ReviewFeedback, original_output: dict) -> dict:
        """Revise the agent's output based on review feedback.

        Only applicable to Author agents. Reviewer agents raise NotImplementedError.
        """
        ...

    def can_auto_fix(self, issue: Issue) -> bool:
        """Check if an issue can be auto-fixed without human intervention."""
        return issue.severity in (IssueSeverity.MINOR, IssueSeverity.SUGGESTION)

    def record_review(self, record: ReviewRecord) -> None:
        """Append a review record to the history."""
        self.review_history.append(record)

    def get_unresolved_blockers(self) -> list[dict]:
        """Get all unresolved blocker issues from the most recent review."""
        if not self.review_history:
            return []
        latest = self.review_history[-1]
        return [i for i in latest.issues if i.get("severity") == "blocker"]

    def iteration_limit_reached(self, max_rounds: int = 3) -> bool:
        """Check if the maximum number of review iterations has been reached."""
        return len(self.review_history) >= max_rounds


# ── QC-5 Quality Model ──

class QCDimension(str, Enum):
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    QUALITY = "quality"
    EXECUTABILITY = "executability"
    COMPLIANCE = "compliance"


# Default QC-5 weights per stage (from agent-collaboration-protocol.md)
QC_WEIGHTS: dict[str, dict[str, float]] = {
    "script": {
        "completeness": 0.25,
        "consistency": 0.15,
        "quality": 0.35,
        "executability": 0.15,
        "compliance": 0.10,
    },
    "assets": {
        "completeness": 0.20,
        "consistency": 0.40,
        "quality": 0.25,
        "executability": 0.10,
        "compliance": 0.05,
    },
    "storyboard": {
        "completeness": 0.15,
        "consistency": 0.30,
        "quality": 0.25,
        "executability": 0.25,
        "compliance": 0.05,
    },
}


def calculate_total_score(dimension_scores: dict[str, int], stage: str) -> int:
    """Calculate weighted total score from dimension scores."""
    weights = QC_WEIGHTS.get(stage, {})
    if not weights:
        return 0
    total = sum(dimension_scores.get(dim, 0) * weight for dim, weight in weights.items())
    return round(total)


def determine_verdict(total_score: int, blocker_count: int) -> Verdict:
    """Determine the review verdict based on score and blocker count.

    Rules (from agent-collaboration-protocol.md):
    - total_score >= 80 AND 0 blockers → APPROVED
    - 65 <= total_score < 80 AND 0 blockers → APPROVED_WITH_MINOR
    - total_score < 65 OR blockers > 0 → NEEDS_REVISION
    """
    if total_score >= 80 and blocker_count == 0:
        return Verdict.APPROVED
    elif 65 <= total_score < 80 and blocker_count == 0:
        return Verdict.APPROVED_WITH_MINOR
    else:
        return Verdict.NEEDS_REVISION
