# Experiments and reproduction

Run `python scripts/evaluate_all.py` from this repository. The report is written to `reports/evaluation-results.json`. This executes real calculations; model quality is separate from test success.

## Recorded baseline

```json
{
  "original": {
    "accuracy": 1.0,
    "macro_f1": 1.0,
    "train_rows": 495,
    "test_rows": 165,
    "features": [
      "subject",
      "age",
      "signal",
      "post_event_result",
      "day"
    ]
  },
  "corrected": {
    "accuracy": 0.43636363636363634,
    "macro_f1": 0.43561734524991724,
    "train_rows": 495,
    "test_rows": 165,
    "features": [
      "age",
      "signal"
    ]
  },
  "strategy": "grouped new-entity holdout",
  "excluded": [
    "post_event_result"
  ],
  "note": "Different split protocols answer different generalization questions. Only explicitly unavailable features are excluded as leaks; correlations remain review findings."
}
```

## Interpretation

Tabular classification audits using explicit task metadata. No guarantee of detecting every kind of leakage.

The raw reports describe whether measurements are synthetic benchmarks, controlled regression fixtures or invariants. Do not interpret regression-fixture accuracy as a held-out real-world score. Preserve seeds and splits when comparing changes.
