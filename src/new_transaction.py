"""
Run the fraud-detection pipeline for a new transaction.

Current flow:
1. Rules engine
2. Big mature-label model
3. Small-model placeholder
4. Most severe verdict wins
"""

from __future__ import annotations

import json
from typing import Any

from big_model.predict import (
    predict_transaction,
)

from label import Label
from rules.rules import check_rules


MODEL_UNUSUAL_THRESHOLD = 0.70
MODEL_SUSPICIOUS_THRESHOLD = 0.90

# True:
# Predict only and do not insert the transaction.
#
# False:
# Allow the transaction insertion section to run.
DRYRUN_FLAG = True


LABEL_SEVERITY = {
    Label.LEGITIMATE: 0,
    Label.UNUSUAL: 1,
    Label.SUSPICIOUS: 2,
}


def read_transaction(
    filename: str,
) -> dict[str, Any]:
    """Read an incoming transaction from JSON."""

    with open(
        filename,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def model_label_to_enum(
    model_label: str,
) -> Label:
    """Convert model output to the shared Label enum."""

    mapping = {
        "legitimate":
            Label.LEGITIMATE,

        "unusual":
            Label.UNUSUAL,

        "suspicious":
            Label.SUSPICIOUS,
    }

    try:
        return mapping[
            model_label
        ]

    except KeyError as error:
        raise ValueError(
            "Unknown big-model label: "
            f"{model_label}"
        ) from error


def most_severe_label(
    *labels: Label,
) -> Label:
    """Return the strongest operational verdict."""

    return max(
        labels,
        key=LABEL_SEVERITY.__getitem__,
    )


def process_transaction(
    transaction: dict[str, Any],
) -> dict[str, Any]:
    """Run the implemented fraud-detection stages."""

    ruleset_result = check_rules(
        transaction,
        DRYRUN_FLAG,
    )

    # A suspicious rules result blocks immediately.
    if (
        ruleset_result
        == Label.SUSPICIOUS
    ):
        return {
            "final_label":
                Label.SUSPICIOUS,

            "ruleset_label":
                ruleset_result,

            "big_model":
                None,

            "small_model":
                None,

            "blocked":
                True,
        }

    big_model_result = (
        predict_transaction(
            transaction,

            unusual_threshold=(
                MODEL_UNUSUAL_THRESHOLD
            ),

            suspicious_threshold=(
                MODEL_SUSPICIOUS_THRESHOLD
            ),
        )
    )

    big_model_label = (
        model_label_to_enum(
            big_model_result[
                "predicted_label"
            ]
        )
    )

    # Add the small-model result here later:
    #
    # small_model_result = ...
    # small_model_label = ...
    #
    # final_result = most_severe_label(
    #     ruleset_result,
    #     big_model_label,
    #     small_model_label,
    # )

    final_result = most_severe_label(
        ruleset_result,
        big_model_label,
    )

    blocked = (
        final_result
        == Label.SUSPICIOUS
    )

    if (
        not DRYRUN_FLAG
        and not blocked
    ):
        # Insert both legitimate and unusual
        # completed transactions here.
        #
        # Database insertion belongs to the
        # transaction-processing layer and is
        # not performed by the big model.
        pass

    return {
        "final_label":
            final_result,

        "ruleset_label":
            ruleset_result,

        "big_model":
            big_model_result,

        "small_model":
            None,

        "blocked":
            blocked,
    }


if __name__ == "__main__":
    result = process_transaction(
        read_transaction(
            "src/test_new_transaction.json"
        )
    )

    print(result)