# Current expanded HLS evidence for Figure4 (20November2026)

Primary:1,241 distinct HLS L30 v2 NBAR cells/61spatial patches. D165/12,E364/11,
H288/14,W339/15,nonveg85/9. All source rows retain nominal95% mapped-cover,
Fmask/context/date/grid criteria. Labels are single-interpreter proposals,
not independently validated ground truth; evergreen structural lidar is older.

Tests retain seven direct-reflectance bands, patch medians and existing fixed
StandardScaler/balanced logistic C1 whole-patch LOPO. Classification58/61correct;
class correct/total11/12,11/11,14/14,13/15,9/9. PooledNPC10/10pairs pass Holm,
giving4/4percategory. Region-conditioned2/3pass;7lackmixedsupport. Pooled
exchangeability across region/season is a strong assumption, not new-region
validation. No control across historical sequential analytical looks is claimed.

NPC uses unchanged synchronized max/integrated statistics, equal band weights
and Holm family10; exact enumeration<=100000assignments, otherwise observed+
99999fixed-input-seededrandomassignments. Current design/computation manifests
and all pair tests/predictions are included. Additional120msource-area
sensitivity362cells/30patches:6/10supported,28/30correct. Pairwise binaryLOPO
meanBA99.7% is a descriptive estimate, not replacement significance.

PanelA uses these exact1241cells, per-cell B1-B5sum normalization and median/IQR.
PanelB uses direct7bandpatchmedians. AOP/drone inputs and styling are retained.
The separate BRDFaudit uses another declared classification protocol and was
not substituted into this table. Human pixel-review guide/atlas and reviewerCSV
remain under provenance/landsat-pure-pixels/2026-11-19/team-validation outside
this compact figure-only folder.
