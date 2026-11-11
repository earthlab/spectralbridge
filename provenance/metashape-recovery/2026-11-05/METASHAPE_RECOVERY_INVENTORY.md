# Recovery inventory

The remote inventory contains 11,665 unique objects totalling 96,106,111,162 bytes across 121 collections under /iplant/home/shared/earthlab/Drone_Calibrations. Ruby and Goldhill are present. Gordon was not found in this collection or the established alternate locations searched; its project recovery remains pending a location/upload.

Retrieval was staged: project descriptors, selected reconstruction assets, full-resolution mosaic tiles, absolute DEM assets and selected original photos. The complete 96.1 GB archive was not downloaded. Large cached per-photo orthophotos remain remote. remote_inventory.json records remote availability; retrieval_manifest.json records exact local paths, sizes, remote MD5 verification and SHA256. A referenced camera filename is not evidence that the photo was downloaded.

Ruby WORKING has chunks 0 and 3, 5,210 camera-plane records, 5,070 aligned planes and 507 aligned exposures in the primary chunk. Goldhill WORKING has 6,090 records, 5,650 aligned planes and 565 aligned exposures. Goldhill NOGCPS-WORKING contains three chunk variants of the same flight, not three independent flights. All have ten sensors. Reports, tie points, panel metadata and surface/mosaic descriptors are available. Raw photo subsets are physically recovered and checksum verified; the remainder are remotely accessible references.

The reliable analysis cache is /private/tmp/spectralbridge-metashape-recovery-20261105/sources. Initial OneDrive photo reads timed out; analysis was rerun from the verified cache. Temporary cache persistence is not archival storage: preserve or rehydrate it using the manifest before another run.

## Portable assets

- `extracted/*/cameras.csv` and `.parquet`: full estimated transforms, centers, reference coordinates, metadata and physical photo-presence flags.
- `extracted/*/sensors.json`: ten band-specific adjusted/initial calibrations and radiometric settings.
- `footprints.geojson`: WGS84 footprints with source projected vertices.
- `geometry_validation.json`, `original_mosaic_binding.json`: internal geometry and source-binding evidence.
- `tie_observations.csv`: final 325 repeated-target measurements; `tie_photo_radiometry.json` records original-photo lineage.
- `repeated_target_fits.json`: support, registration sensitivity and temporal uncertainty.
- `retrieval_manifest.json`: verified staged files; other remote objects remain unmaterialized.

Referenced photographs not downloaded remain explicitly unavailable locally; project variants are not independent observations.
