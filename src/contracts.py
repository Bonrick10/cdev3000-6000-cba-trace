"""Typed result contracts for the fraud-detection pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.label import Label


class Action(str, Enum):
    """Operational action applied to a transaction attempt."""

    APPROVE = "approve"
    APPROVE_AND_ALERT = "approve_and_alert"
    APPROVE_AND_INVESTIGATE = "approve_and_investigate"
    BLOCK = "block"


@dataclass(frozen=True)
class RuleDecision:
    """Result of the pure rules engine."""

    label: Label
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"label": self.label.value, "reasons": list(self.reasons)}


@dataclass(frozen=True)
class FinalDecision:
    """Final label and action, including the stage that decided the route."""

    label: Label
    action: Action
    source: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "label": self.label.value,
            "action": self.action.value,
            "source": self.source,
            "reason": self.reason,
        }


@dataclass
class PipelineResult:
    """JSON-safe evidence returned by transaction processing."""

    final: FinalDecision
    rules: RuleDecision
    big_model: Optional[Dict[str, Any]] = None
    small_model: Optional[Dict[str, Any]] = None
    transaction_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "final_label": self.final.label.value,
            "action": self.final.action.value,
            "decision_source": self.final.source,
            "decision_reason": self.final.reason,
            "rules": self.rules.to_dict(),
            "big_model": self.big_model,
            "small_model": self.small_model,
            "model_versions": {
                "big_model": (self.big_model or {}).get("model_version"),
                "small_model": (self.small_model or {}).get("model_version"),
            },
        }
