"""Source-aware final decision logic."""

from typing import Dict

from src.contracts import Action, FinalDecision
from src.label import Label

MODEL_SEVERITY: Dict[Label, int] = {
    Label.LEGITIMATE: 0,
    Label.UNUSUAL: 1,
    Label.SUSPICIOUS: 2,
}


def decision_for_rule_exit(label: Label) -> FinalDecision:
    """Return the terminal decision for a rule-owned route."""
    mapping = {
        Label.RULE_APPROVAL: (Action.APPROVE, "known recurring transaction"),
        Label.RULE_ALERT: (Action.APPROVE_AND_ALERT, "explicit unusual rule triggered"),
        Label.RULE_VIOLATION: (Action.BLOCK, "explicit blocking rule triggered"),
    }
    try:
        action, reason = mapping[label]
    except KeyError as error:
        raise ValueError(f"{label.value} is not a terminal rules label.") from error
    return FinalDecision(label, action, "rules", reason)


def combine_model_labels(big_label: Label, small_label: Label) -> FinalDecision:
    """Use the worse model label while never blocking a model-owned verdict."""
    try:
        final_label = max((big_label, small_label), key=MODEL_SEVERITY.__getitem__)
    except KeyError as error:
        raise ValueError(
            "Models may only return legitimate, unusual, or suspicious."
        ) from error

    actions = {
        Label.LEGITIMATE: Action.APPROVE,
        Label.UNUSUAL: Action.APPROVE,
        Label.SUSPICIOUS: Action.APPROVE_AND_ALERT,
    }
    return FinalDecision(
        final_label,
        actions[final_label],
        "models",
        f"maximum severity of big={big_label.value} and small={small_label.value}",
    )
