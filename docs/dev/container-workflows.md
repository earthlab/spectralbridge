# Container and Remote Helper Scripts

SpectralBridge is often run inside containers or cloud instances where mounted
storage paths do not match local development paths. A few root-level helper
scripts intentionally remain at the repository root because those workflows
invoke them from container entry points or mounted working directories.

## Root Helpers

- `gocmd` is the root-level GoCommands binary used by CyVerse/iRODS transfer
  workflows.
- `move_folders_from_instance_to_remote.py` helps move completed output folders
  from a compute instance to remote storage.
- `remote_to_instance.py` helps copy remote data down to the compute instance
  before processing.
- `patch_script_toworkfromcorrectedfiles.py` is a workflow-specific patch helper
  retained for reproducibility of the corrected-file workflow.

These files are active operational helpers, not importable SpectralBridge
package modules. They are excluded from source distributions by `MANIFEST.in`
so package users do not receive container-specific tooling by accident.

If these workflows are replaced, move the retired scripts to `deprecated/`
instead of deleting them.
