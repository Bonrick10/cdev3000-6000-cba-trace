"""Human-readable terminal output for fraud-pipeline demonstrations."""

from __future__ import annotations

from typing import Any, Mapping

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"


def _style(text: object, *codes: str, enabled: bool) -> str:
    value = str(text)
    return f"{''.join(codes)}{value}{_RESET}" if enabled else value


def _label(value: object, *, color: bool) -> str:
    text = str(value or "not_run").upper().replace("_", " ")
    code = {
        "LEGITIMATE": _GREEN,
        "RULE APPROVAL": _GREEN,
        "UNUSUAL": _YELLOW,
        "RULE ALERT": _YELLOW,
        "SUSPICIOUS": _RED,
        "RULE VIOLATION": _RED,
        "NOT RUN": _DIM,
    }.get(text, _CYAN)
    return _style(text, _BOLD, code, enabled=color)


def _percentage(value: object, digits: int = 2) -> str:
    return "—" if value is None else f"{float(value):.{digits}f}%"


def _number(value: object, digits: int = 2) -> str:
    return "—" if value is None else f"{float(value):.{digits}f}"


def _section(title: str, *, color: bool) -> str:
    return _style(title, _BOLD, _CYAN, enabled=color)


def format_pipeline_result(
    result: Mapping[str, Any], *, persisted: bool, color: bool = False
) -> str:
    """Format a pipeline result for a person watching a terminal demo."""
    rules = result.get("rules") or {}
    big = result.get("big_model") or {}
    small = result.get("small_model") or {}
    action = str(result.get("action", "unknown")).upper().replace("_", " ")

    lines = [
        "",
        _style(
            "╭────────────────────────────────────────────────────────────╮",
            _CYAN,
            enabled=color,
        ),
        _style(
            "│             FRAUD DETECTION PIPELINE RESULT                │",
            _BOLD,
            _CYAN,
            enabled=color,
        ),
        _style(
            "╰────────────────────────────────────────────────────────────╯",
            _CYAN,
            enabled=color,
        ),
        "",
        _section("FINAL DECISION", color=color),
        f"  {_label(result.get('final_label'), color=color)}  →  "
        f"{_style(action, _BOLD, enabled=color)}",
        "  Source : "
        f"{str(result.get('decision_source', 'unknown')).replace('_', ' ').title()}",
        f"  Reason : {result.get('decision_reason', '—')}",
        "",
        _section("PIPELINE EVIDENCE", color=color),
        f"  1  Rules engine   {_label(rules.get('label'), color=color)}",
    ]

    reasons = rules.get("reasons") or []
    lines.append(
        f"     Triggered      {', '.join(map(str, reasons))}"
        if reasons
        else "     Triggered      No blocking or alert rules"
    )

    if big:
        unusual = big.get("unusual_threshold")
        suspicious = big.get("suspicious_threshold")
        unusual_text = _percentage(float(unusual) * 100) if unusual is not None else "—"
        suspicious_text = (
            _percentage(float(suspicious) * 100) if suspicious is not None else "—"
        )
        lines.extend(
            [
                "  2  Big model      "
                f"{_label(big.get('predicted_label'), color=color)}",
                f"     Fraud risk     {_percentage(big.get('risk_score'))}",
                "     Thresholds     "
                f"unusual {unusual_text}  •  suspicious {suspicious_text}",
            ]
        )
    else:
        lines.append(f"  2  Big model      {_label(None, color=color)} (rules exit)")

    if small:
        count = small.get("reported_fraud_count")
        size = small.get("cluster_size")
        ratio = (
            f"{count}/{size} reported fraud"
            if count is not None and size is not None
            else "—"
        )
        confidence = small.get("membership_confidence")
        confidence_text = (
            _percentage(float(confidence) * 100) if confidence is not None else "—"
        )
        lines.extend(
            [
                "  3  Small model    "
                f"{_label(small.get('predicted_label'), color=color)}",
                "     Fraud pattern  "
                f"Cluster {small.get('cluster_id', '—')}  •  {ratio}",
                "     Cluster risk   "
                f"{_percentage(small.get('reported_fraud_percentage'))}  •  "
                "Wilson lower bound "
                f"{_percentage(small.get('fraud_rate_lower_bound'))}",
                "     Assignment     "
                f"distance {_number(small.get('assignment_distance'))}  •  "
                f"confidence {confidence_text}",
            ]
        )
    else:
        lines.append(f"  3  Small model    {_label(None, color=color)} (rules exit)")

    transaction_id = result.get("transaction_id")
    persistence = (
        f"SAVED TO DATABASE  •  transaction #{transaction_id}"
        if persisted
        else "DRY RUN  •  no transaction was written to the database"
    )
    lines.extend(["", _style(f"  {persistence}", _DIM, enabled=color), ""])
    return "\n".join(lines)
