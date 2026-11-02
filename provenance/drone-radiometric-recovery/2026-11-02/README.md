# Goldhill isolated radiometric recovery experiment

See [scientific report](../../../docs/dev/drone-radiometric-recovery-experiment.md).

Run `run_experiment.py`, then `plot_experiment.py`, `write_report.py` and `make_pdf.py` from repo root. Large actual-data arrays and recovered TIFFs are under the work directory recorded in `experiment_manifest.json`; source locations/remote origins are inherited from the verified October 30 scale evidence. No production artifacts are overwritten. `historical_corrections.py` is an exact GPL-covered historical module used only for invalid-model replay, not an alternative production implementation.
