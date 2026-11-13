# Model and simulator card — Dataset Crime Scene

## Intended use

A tabular data-forensics tool that distinguishes confirmed metadata violations from suspicious correlations.

## Implemented methods

- CSV ingestion with target, entity and time configuration
- Exact duplicates, missingness and entity-overlap checks
- Target-proxy correlation findings marked for review
- Prediction-time availability metadata and split correction
- Original versus corrected random-forest classification evaluation

Some projects use deterministic simulators and rules rather than trained neural models. Those distinctions are retained in this card and the source.

## Evaluation

See `docs/EXPERIMENTS.md` and the machine-readable reports. No pretrained foundation-model weights or real-world efficacy certification are included. Parameters, splits and synthetic generators are visible in source.

## Limitations

Tabular classification audits using explicit task metadata. No guarantee of detecting every kind of leakage.

## Extensions not implemented in this release

- Pipeline instrumentation and temporal feature availability audits
- Near-duplicate methods and broader corruption-family benchmarks
