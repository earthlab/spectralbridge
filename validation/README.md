# Validation Records

This directory separates validation plans from validation evidence.

- `campaigns/*.example.json` describes a proposed campaign and resource scope.
  An example manifest is not evidence that the campaign ran.
- `results/*.json` is immutable machine-readable output from a completed
  campaign. Website pages under `docs/validation/` are generated from it.

Use:

```bash
python scripts/run_validation_campaign.py --help
python scripts/generate_validation_docs.py --check
```

`offline-contract.json` validates deterministic function and file contracts. It
does not claim external scientific accuracy or represent 100 live NEON runs.

