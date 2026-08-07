"""Common Pydantic schemas: error response, pagination, agent messages."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Error ──

class ErrorDetail(BaseModel):
    """A single error detail."""
    code: str
    message: str
    field: str | None = None
    detail: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error response for all API endpoints."""
    success: bool = False
    error: ErrorDetail
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Pagination ──

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int


# ── Agent Message ──

class AgentMessage(BaseModel):
    """Structured message between agents (as defined in agent-collaboration-protocol.md)."""
    message_id: str
    timestamp: str
    sender: dict  # {agent_id, role}
    recipient: dict  # {agent_id, role}
    message_type: str  # review_feedback | revision_response | clarification | escalation
    target_artifact: dict  # {artifact_type, artifact_ref, version}
    content: dict  # {overall_verdict, score, critical_issues, strengths, continuity_flags}
    iteration_round: int = 1
    ttl_rounds_remaining: int = 3
    reply_to: str | None = None


class ReviewFeedback(BaseModel):
    """Review feedback from a reviewer agent."""
    overall_verdict: str  # approved | approved_with_minor | needs_revision | rejected
    total_score: int = Field(ge=0, le=100)
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    critical_issues: list[dict] = Field(default_factory=list)
    strengths: list[dict] = Field(default_factory=list)
    continuity_flags: list[dict] = Field(default_factory=list)
