# Container and Remote Helper Scripts

SpectralBridge is often run inside containers or cloud instances where mounted
storage paths do not match local development paths. A few root-level helper
scripts intentionally remain at the repository root because those workflows
invoke them from container entry points or mounted working directories.

## Run the package in a fresh container

From the cloned repository mounted as the working directory:

```bash
python -m pip install -e .
python examples/run_neon_pipeline.py --check
```

The check validates and resolves the example JSON without contacting NEON.
Mount a persistent output volume, edit
`examples/config/neon_pipeline.example.json`, then rerun without `--check`.
For JupyterLab, install `-e ".[notebooks]"` and open
`docs/vignettes/notebooks/`.

## Site-specific root helpers

- `gocmd` is the root-level GoCommands binary used by CyVerse/iRODS transfer
  workflows.
- `move_folders_from_instance_to_remote.py` helps move completed output folders
  from a compute instance to remote storage.
- `remote_to_instance.py` helps copy remote data down to the compute instance
  before processing.
- `patch_script_toworkfromcorrectedfiles.py` is a historical runtime-patching
  experiment retained for provenance; new work should use normal restart
  behavior or the documented custom-correction hook.

The transfer files are maintainer operational helpers, not general package
entry points or importable SpectralBridge modules. They are excluded from source
distributions by `MANIFEST.in` so package users do not receive
infrastructure-specific tooling by accident.

If these workflows are replaced, move the retired scripts to `deprecated/`
instead of deleting them.
