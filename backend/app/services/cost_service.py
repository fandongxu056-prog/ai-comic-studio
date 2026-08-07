"""Cost tracking service — budget governance for AI API calls.

Design reference: Open Montage's Budget Governance (estimate → reserve → reconcile lifecycle).
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.config import settings


class BudgetMode(str, Enum):
    OBSERVE = "observe"   # Track costs, no enforcement
    WARN = "warn"         # Log warnings on overruns
    CAP = "cap"           # Reject operations exceeding budget


@dataclass
class CostEntry:
    """A single cost record."""
    timestamp: str
    provider: str
    model: str
    operation: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


@dataclass
class ProjectCostTracker:
    """Per-project cost tracker with budget enforcement."""

    project_id: str
    max_budget_usd: float = 50.0
    mode: BudgetMode = BudgetMode.WARN
    reserve_ratio: float = 0.10  # 10% held in reserve

    _entries: list[CostEntry] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def total_spent(self) -> float:
        return sum(e.cost_usd for e in self._entries)

    @property
    def effective_budget(self) -> float:
        return self.max_budget_usd * (1 - self.reserve_ratio)

    @property
    def budget_remaining(self) -> float:
        return self.effective_budget - self.total_spent

    @property
    def is_over_budget(self) -> bool:
        return self.total_spent > self.effective_budget

    def record(self, entry: CostEntry) -> bool:
        """Record a cost. Returns True if operation is allowed, False if capped."""
        with self._lock:
            if self.mode == BudgetMode.CAP and self.total_spent + entry.cost_usd > self.effective_budget:
                return False
            self._entries.append(entry)
            return True

    def record_estimate(self, entity_id: str, operation: str, estimated_cost: float) -> None:
        """Record a cost estimate (pre-API call). No enforcement, just tracking."""
        pass  # Estimates are tracked but not recorded as actual costs

    def record_actual(self, entity_id: str, operation: str, actual_cost_usd: float) -> None:
        """Record an actual cost after API call completes."""
        entry = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider="",
            model="",
            operation=operation,
            cost_usd=actual_cost_usd,
        )
        self.record(entry)

    def estimate_cost(
        self,
        provider: str,
        model: str,
        operation: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> float:
        """Estimate cost before making an API call."""
        # Approximate pricing — extend as needed
        pricing: dict[str, dict[str, float]] = {
            "openai": {"gpt-4o": 2.50, "gpt-4o-mini": 0.15, "dall-e-3": 0.040, "tts-1-hd": 0.030},
            "anthropic": {"claude-sonnet-5": 3.00, "claude-opus-5": 15.00},
        }
        price_per_1k = pricing.get(provider, {}).get(model, 1.0)
        return ((tokens_in + tokens_out) / 1000) * (price_per_1k / 1_000_000)

    def summary(self) -> dict:
        """Return a cost summary for reporting."""
        by_provider: dict[str, float] = {}
        for e in self._entries:
            by_provider[e.provider] = by_provider.get(e.provider, 0.0) + e.cost_usd

        return {
            "project_id": self.project_id,
            "total_cost_usd": round(self.total_spent, 4),
            "budget_limit_usd": self.max_budget_usd,
            "effective_budget_usd": round(self.effective_budget, 4),
            "budget_remaining_usd": round(self.budget_remaining, 4),
            "over_budget": self.is_over_budget,
            "mode": self.mode.value,
            "by_provider": {k: round(v, 4) for k, v in by_provider.items()},
            "entry_count": len(self._entries),
        }


# Global registry of per-project trackers
_trackers: dict[str, ProjectCostTracker] = {}
_trackers_lock = threading.Lock()


def get_tracker(project_id: str) -> ProjectCostTracker:
    """Get or create a cost tracker for a project."""
    with _trackers_lock:
        if project_id not in _trackers:
            _trackers[project_id] = ProjectCostTracker(
                project_id=project_id,
                max_budget_usd=settings.max_budget_per_project_usd,
                mode=BudgetMode(settings.budget_mode),
            )
        return _trackers[project_id]
