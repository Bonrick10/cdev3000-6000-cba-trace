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
   `suspicious` results are approved and investigated; only a
   `rule_violation` blocks.

Every persisted attempt has a `transaction_decisions` row preserving rules,
model evidence, versions, final label, and action.

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
```

No migration runs automatically. The repository also does not reset or
regenerate a remote database during model training.

## Commands

```bash
python -m src.main train-big
python -m src.main train-small
python -m src.main process src/test_new_transaction.json
python -m src.main report 123 confirmed_fraudulent
python -m src.main refresh-small
pytest
ruff check .
```

The big and small models read their development population from the
`txns_testing` backup table. Live rules, insertion, corrections, and decision
evidence continue to use `transactions`; keeping the backup synchronized is a
data-generation responsibility. The big model retains only rows older than the
two-calendar-month maturity cutoff, creates every row from strictly prior
history, maps mature labels only in memory, and saves the complete preprocessing
pipeline with `joblib`.

The small model excludes all rules-bypassed attempts, fits candidate fraud
clusters using behavioural features only, assigns the eligible population,
and applies support, fraud-count, Wilson-bound, and assignment-distance
controls. K-Means is used for maintainable live assignment; MiniBatchKMeans is
selected automatically for at least 50,000 confirmed fraud rows. Cluster IDs
are valid only with their stored model version.

Customer corrections are recorded atomically. Cluster statistics can refresh
immediately without changing centroids; confirmed fraud feedback also marks a
periodic cluster rebuild as recommended.
