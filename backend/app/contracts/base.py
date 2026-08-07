"""Cross-stage continuity contract framework.

Implements the 16 contract rules defined in docs/agent-collaboration-protocol.md §5.
Each rule validates that downstream stage outputs correctly reference upstream artifacts.
"""

from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field


class ViolationLevel(str, Enum):
    BLOCKER = "blocker"  # Prevent entering next stage
    MAJOR = "major"      # Allow but flag for human confirmation
    MINOR = "minor"      # Auto-record warning, don't block


class ContractRule(BaseModel):
    """A single contract validation rule."""
    id: str
    type: str  # entity_coverage, style_alignment, costume_logic, etc.
    description: str
    validation: str  # Human-readable description of the validation
    on_violation: ViolationLevel


class ContractViolation(BaseModel):
    """A contract violation found during validation."""
    rule_id: str
    level: ViolationLevel
    description: str
    details: dict[str, Any] = Field(default_factory=dict)


class ContractResult(BaseModel):
    """Result of running all contract validations."""
    passed: bool
    violations: list[ContractViolation] = Field(default_factory=list)
    warnings: list[ContractViolation] = Field(default_factory=list)

    @property
    def blocker_count(self) -> int:
        return sum(1 for v in self.violations if v.level == ViolationLevel.BLOCKER)

    @property
    def can_proceed(self) -> bool:
        """Can the pipeline proceed to the next stage?"""
        return self.blocker_count == 0


class BaseContract:
    """Base class for stage-to-stage contracts."""

    rules: list[ContractRule] = []
    from_stage: str = ""
    to_stage: str = ""

    async def validate(self, upstream_data: dict, downstream_data: dict) -> ContractResult:
        """Run all contract rules. Override in subclasses with specific logic."""
        result = ContractResult(passed=True)
        for rule in self.rules:
            # Subclasses implement _check_rule
            violations = await self._check_rule(rule, upstream_data, downstream_data)
            for v in violations:
                if v.level == ViolationLevel.BLOCKER:
                    result.violations.append(v)
                    result.passed = False
                elif v.level == ViolationLevel.MAJOR:
                    result.violations.append(v)
                else:
                    result.warnings.append(v)
        return result

    async def _check_rule(
        self, rule: ContractRule, upstream: dict, downstream: dict
    ) -> list[ContractViolation]:
        """Check a single contract rule. Override in subclasses."""
        return []
