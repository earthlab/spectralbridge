# Landsat search and selection

Source: Planetary Computer STAC, collection `landsat-c2-l2`. Saved unsigned `search_items.json` contains all eight returned items and asset metadata. Search covered the flight footprint and calendar dates 2021-08-30 through 2021-10-01 (exclusive end 2021-10-02); individual exact-hour window indicators remain in `scene_candidates.csv`. Calendar boundary scenes can fall slightly beyond 16 x 24 hours.

Three candidates are Landsat 8 OLI Collection 2 Level-2: September 16, September 7, August 31. Five ETM+ candidates remain in the ledger but cannot validate the seven OLI channels, including coastal. The same-day September 15 ETM+ scene is explicitly excluded for sensor incompatibility, not poor agreement.

The selected product is **LC08_L2SP_033032_20210916_20210925_02_T1**, STAC item LC08_L2SP_033032_20210916_02_T1. Actual timestamp: 2021-09-16 17:37:35.213645 UTC; cloud cover 0.19%; sun elevation 48.4929 degrees; sun azimuth 151.4204 degrees. Footprints/platform/sensor/collection/level and every candidate are machine-readable. September 16 had 3,583 usable pixels out of 3,600 with sufficient NEON coverage (99.5278%). Older compatible candidates each had 3,600; the next-day scene won by the predeclared temporal-first ranking, not better agreement.

For this **one** flight: compatible same-day availability 0/1; <=1, <=3 and <=7 days each 1/1 under the stated UTC interpretation. Across-flight availability rates cannot be estimated. Same-day any-sensor availability is 1/1, but ETM+ cannot be substituted for OLI.

The legacy H5 timestamp is `2021-09-15, 191530 [Computer Time in sec]`, without an explicit timezone. UTC is an interpretation based on NEON's general convention, not independently verified for this legacy field. The +22.3681 h time difference and <=1-day classification are conditional on that basis. The September 16 versus September 15 calendar-day distinction is clear; no near-simultaneous gold-standard claim is made.

Only selected seven-band SR and candidate QA crops were read. Ephemeral signed access tokens are not evidence; saved item URLs are unsigned. The raster-window cache is ignored by Git, identified by checksums in the original run manifest. No full Landsat scene was downloaded.
