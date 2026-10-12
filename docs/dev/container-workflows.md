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
  from a compute instance to remote storage. Pass one or more local sources
  followed by one CyVerse destination (the last argument). A source may be a
  folder or a single file. Notebooks should call
  `run_transfer(*sources, destination)`. Default transfer flags are
  `gocmd put --quiet -f --diff --no_hash`. Jupyter checkpoints are omitted.
  Failures are appended to `gocmd_upload_failures.log` and the next file still
  runs.
- `remote_to_instance.py` helps copy remote data down to the compute instance
  before processing.
- `patch_script_toworkfromcorrectedfiles.py` is a workflow-specific patch helper
  retained for reproducibility of the corrected-file workflow. For new work
  prefer `scripts/run_pipeline_from_corrected_envi.py`, which resumes from the
  same corrected ENVI products but reuses a genuine raw ENVI and correction JSON
  when they exist and records any substitution it has to make.

The transfer files are maintainer operational helpers, not general package
entry points or importable SpectralBridge modules. They are excluded from source
distributions by `MANIFEST.in` so package users do not receive
infrastructure-specific tooling by accident.

If these workflows are replaced, move the retired scripts to `deprecated/`
instead of deleting them.

## Installing the CyVerse transfer client

SpectralBridge's remote backend calls an existing `gocmd` client on `PATH`.
Install GoCommands for your OS/CPU using the [official CyVerse installation
instructions](https://learning.cyverse.org/ds/gocommands/installation/) or the
[upstream release assets](https://github.com/cyverse/gocommands/releases).
For a Conda environment, upstream documents `conda install -c conda-forge gocommands`.
Record the selected upstream release/version and binary checksum with your campaign configuration;
no particular upstream version is newly certified by this repository cleanup.

The root `./gocmd` is now a compatibility launcher over your installed client.
Set `GOCMD_BINARY=/absolute/path/to/gocmd` when using a nonstandard installation.
It forwards all arguments and preserves the working directory. Configure your
existing authentication outside SpectralBridge; the cleanup does not alter it.
The old Linux x86-64 binary is preserved only in this checkout's ignored local
archive for historical replay. It is absent from fresh clones and distributions.
The scientific pipeline does not require gocmd unless using a CyVerse backend.
