# CBA Trace fraud detection

The transaction pipeline separates known rules, global supervised risk, and
emerging fraud-pattern monitoring:

1. Rules either block as `rule_violation`, approve as `rule_approval`, approve
   and alert as `rule_alert`, or pass the attempt to both models.
2. The big model is a leakage-safe logistic-regression probability model.
3. The small model learns versioned K-Means fraud neighbourhoods from
   `confirmed_fraudulent` transactions and profiles the eligible wider
   population around them.
4. The post-rules decision uses the more severe model label. Model-owned
   `suspicious` results are approved and alerted; only a
   `rule_violation` blocks.

Every persisted attempt has a `transaction_decisions` row preserving rules,
model evidence, versions, final label, and action.

## Labels and outcomes

- `confirmed_legitimate`: confirmed by the customer to be legitimate.
- `legitimate`: assessed as normal; approve.
- `unusual`: outside usual behaviour; approve.
- `suspicious`: potential fraud or scam; approve and alert.
- `confirmed_fraudulent`: confirmed by the customer after processing.
- `rule_violation`: a blocking rule triggered; block before model evaluation.
- `rule_approval`: a high-confidence approval rule triggered; approve and bypass
  both models.
- `rule_alert`: an explicit unusual rule triggered; approve and alert while
  bypassing both models.

`approve_and_alert` is the single operational alert bucket. Its evidence and
decision source distinguish a rules-owned alert from a model-owned suspicious
assessment.

## Rules and precedence

When several rules trigger, the safety order is `rule_violation` > `rule_alert`
> `rule_approval`:

- At least five matching payments older than seven days to the same payee,
  within $5 and 30 minutes of the current time of day: `rule_approval`.
- Previously unseen customer device: `rule_alert`.
- Current transaction plus prior 24-hour spending exceeds prior seven-day
  spending: `rule_alert`.
- Travel faster than 500 km/h from the previous transaction: `rule_violation`.
- More than $10,000 to a new payee: `rule_alert`.
- Outside the usual merchant-category amount range: `rule_alert`.
- Outside the suspicious merchant-category amount range: `rule_violation`.

Device, spending-history, and new-payee alerts are skipped while an account has
fewer than five prior transactions or less than 15 days of history. Those
signals do not have a meaningful baseline for a genuinely fresh account;
merchant limits still apply.

## Setup

Python 3.11 or later is required.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Set `DATABASE_URL` in `.env`. Do not commit that file.

For a fresh database only:

```bash
psql "$DATABASE_URL" -f src/db_init/sql/schema.sql
psql "$DATABASE_URL" -f src/db_init/sql/synthetic_population.sql
```

For an existing database, back it up and run the migrations individually and
in order. The enum migration must commit before the new value is referenced:

```bash
psql "$DATABASE_URL" -f src/db_init/sql/migrations/001_add_rule_alert.sql
psql "$DATABASE_URL" -f src/db_init/sql/migrations/002_transaction_decisions.sql
psql "$DATABASE_URL" -f src/db_init/sql/migrations/003_pipeline_indexes.sql
psql "$DATABASE_URL" -f src/db_init/sql/migrations/004_reported_fraud_support.sql
```

No migration runs automatically. The repository also does not reset or
regenerate a remote database during model training.

## Commands

```bash
python -m src.main train-big
python -m src.main train-small
python -m src.main evaluate
# Dry run: evaluate without inserting database rows
python -m src.main process src/test_new_transaction.json
# Explicitly persist the transaction and decision evidence
python -m src.main process src/test_new_transaction.json --persist
python -m src.main report 123 confirmed_fraudulent
python -m src.main refresh-small
pytest
ruff check .
```

Transaction processing defaults to a dry run for safe demos and testing. A dry
run still reads historical context and runs the complete rules/model pipeline,
but it does not insert into `transactions` or `transaction_decisions`. Pass
`--persist` only when those rows should be recorded.

The big and small models read their development population from the canonical
`full_txns` snapshot. Live rules, insertion, corrections, and decision evidence
continue to use `transactions`; keeping the snapshot synchronized is a
data-generation responsibility. In the snapshot, `true_label` is hidden ground
truth. It is used only as the mature big-model target and for final evaluation.
`predicted_label` is the status observable at the time: it identifies rule exits
and `reported_fraud` seeds. Neither column is a behavioural model feature. The
big model retains only rows older than the
two-calendar-month maturity cutoff, creates every row from strictly prior
history, maps mature true labels only in memory, and saves the complete
preprocessing pipeline with `joblib`.

The small model excludes all rules-bypassed attempts and uses the complete
rolling 60-day eligible population. It fits fraud-pattern centroids only from
rows whose observable status is `reported_fraud`, then assigns the rest of the
window to those neighbourhoods. By default, `unusual` begins at a smoothed 5%
report rate. `suspicious` requires a smoothed 10% report rate, an 8% Wilson lower
bound, at least 100 accepted transactions, and at least 20 reports. Environment
variables can override all thresholds.

`python -m src.main evaluate` performs a read-only in-memory evaluation and
prints a stakeholder-readable comparison of the big model, small model, and
combined decision. Add `--json` for machine-readable output. Hidden truth is
revealed only when calculating precision, recall, false-positive rate, and
captured fraud value.

Older rows remain available only while constructing leakage-safe prior-history
features. Each confirmed customer fraud report triggers a complete versioned
rebuild of the current window, naturally evicting expired population rows.

It fits candidate fraud clusters using behavioural features only, assigns the
eligible population, and applies support, fraud-count, Wilson-bound, and
assignment-distance controls. K-Means is used for maintainable live assignment;
MiniBatchKMeans is selected automatically for at least 50,000 reported fraud
rows. Cluster IDs are valid only with their stored model version.

Prediction assigns a new transaction to the nearest supported fraud
neighbourhood but never mutates its centroid. The assignment and cluster
evidence are persisted in `transaction_decisions`; centroids change only during
a versioned rebuild.

Customer corrections are recorded atomically. Confirmed fraud feedback then
rebuilds both centroids and cluster statistics from the current rolling window.

`transaction_decisions` is the audit record for routing and outcomes. Historical
development routing comes from the observable `predicted_label` in `full_txns`.
The audit table preserves the exact model versions and evidence that produced
each persisted live decision.
