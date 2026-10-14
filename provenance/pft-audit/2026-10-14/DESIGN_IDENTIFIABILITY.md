# Design, estimands and identifiability

Measured from the corrected compact source and verified statistics ledger on 2026-10-14; see [DESIGN_METRICS.json](DESIGN_METRICS.json), [cohort_support.csv](cohort_support.csv), [species_support.csv](species_support.csv) and [species_site_year.csv](species_site_year.csv).

```text
3 sites: NIWO, WREF, YELL
  site × acquisition year: NIWO 2020/2023; WREF/YELL 2023 only
    122 flight/source pairs (one source per flight in this extraction)
      plant ↔ flight: crossed/repeated within site, not plant nested in one flight
        8,845 polygon/flight observations, 1–8 per GlobalID (median 3)
          pixels reduced to a per-observation median before inference
    2,496 GlobalID crown/plant proxies, one site each
      886 recur across years, all at NIWO (715 assigned PFT plants)
      3,382 plant-years; 2,659 assigned plant-years / 1,944 assigned identities
species (57 labels; 42 assigned taxa) → deterministic PFT lookup (5 classes)
  species partly crossed with site: 12 assigned taxa occur at >1 site
  plant nested within species; species nested within assigned PFT
representation: raw / corrected / synthetic OLI / synthetic MicaSense
  paired deterministic representations, not independent acquisitions
wavelength: correlated coordinates within one curve; not replicate plants
```

Polygon IDs are local rasterization indices and can change by source. The GlobalID is the repeated biological-object proxy. The supplied data cannot certify that distinct IDs never represent overlapping crowns or ramets. Source coordinate fields exist in the pixel table, but the current compact inferential data do not model spatial covariance. Site/year/flight/source history comes from checked filenames and acquisition provenance, not field-survey year.

The 15 unresolved source labels exclude 552 identities; their missing PFT assignment is not assumed random. Variable-habit flags and source references in the crosswalk are not individual trait validation. Conclusions cover the assigned sampled taxa only.

The common corrected grid has 426 nominal samples, of which 360 are complete across assigned plants in each cohort after existing gap policy. Missing regions are deliberately unsupported, not zeros. No analysis may turn the union of native grids into a single unverified spectrum.

## Species replication and support

| PFT | Name | Assigned taxa globally | Main limitation |
| --- | --- | ---: | --- |
| DBS | Deciduous broadleaf shrubs | 18 | Many taxa have 1–4 plants; dominance and geography vary |
| DBT | Deciduous broadleaf trees | 7 | Only two taxa in each NIWO cohort; different mix at WREF |
| EBS | Evergreen broadleaf shrubs | 3 | 64/68 identities are Artemisia tridentata; WREF has three plants |
| ECS | Evergreen conifer shrubs | 1 | All 29 identities are Juniperus communis |
| ECT | Evergreen conifer trees | 13 | Large sample, but three taxa dominate; species share sites unevenly |

These counts include all assigned taxa, not just taxa with ≥10 plants in earlier species figures. Exact flight-history contrasts have 3–30 mixed blocks, with 0–18 singleton PFT/block cells. Only 21/40 corrected cohort/pair candidates meet the 10-per-PFT matched support rule; 33/40 meet it without flight conditioning. Absence at a site and insufficient matched support are not evidence of identical spectra.

## H1–H6: what is identifiable?

| Hypothesis | Supported design / estimand | Boundary |
| --- | --- | --- |
| H1 sampled-group association | Within-cohort curves from the sampled PFT/species mixtures; plant is the unit | Conditional exchangeability, spatial/species composition limitations; not pure PFT mechanism |
| H2 acquisition-robust association | PFT contrast within exact shared exposure histories | Narrow overlap subset; history is not every acquisition/canopy interaction |
| H3 cross-site consistency | Compare signed curves on common bands at the three 2023 sites | Only three sites; NIWO 2020 is repeat-site context, not fourth site; descriptive recurrence ≠ random-site population inference |
| H4 species-independent PFT | Not identifiable with unrestricted species fixed effects | Species matrix rank 42; species+PFT matrix rank 42. PFT lies exactly in species column space |
| H5 generalization | Selected held-out species/sites/years can be studied prospectively | No existing held-out PFT evaluation; some class/fold combinations unsupported; transfer is context-specific |
| H6 classification/detection | Future grouped prediction study with sensitivity/specificity, calibration, prevalence and abstention | Current hypothesis tests measure neither accuracy nor utility |

## Which mixed model is supportable?

For observation-level curves, a restrained model could use site as a fixed context, within-NIWO year as a fixed contrast, flight functions within site/year and plant random functions across repeated flights/years. Plants and flights are crossed. Products are paired transformations and should normally be analyzed separately. A fixed site+year model estimates its year term through NIWO alone; it must not extrapolate a common temporal response to WREF/YELL. A full site×year interaction has empty cells.

Adding all species fixed-effect functions to a PFT fixed-effect model is rank deficient. Replacing species with random functions nested within PFT changes the target: PFT hypermeans become estimates under a zero-mean/exchangeable species distribution and a covariance/pooling model. That is a substantive assumption, not automatic species adjustment. It may be useful for DBS/DBT/ECT, but ECS has no within-PFT species replication, and EBS is strongly dominated by one species. Even a converged hierarchical model cannot demonstrate an independently replicated ECS PFT effect. Do not fit every possible random effect to plant/year medians: the flight-level information needed for those components was already reduced.

Functional mixed/additive models are legitimate tools ([Morris & Carroll, 2006](https://doi.org/10.1111/j.1467-9868.2006.00539.x); [Scheipl et al., 2015](https://doi.org/10.1080/10618600.2014.901914)). Their structural flexibility does not restore this missing design replication. A reduced block fixed-effects functional response model is estimable and is compared in a label-blind FPCA subspace; it makes no random-species claim.

## Meaningful validation designs

| Split | Feasible use | Leakage / support condition |
| --- | --- | --- |
| Leave one plant out | New individuals in sampled contexts | Every observation/year/product of a GlobalID must stay together; training-only preprocessing |
| Leave one flight out | Acquisition transfer | Exclude all training observations of test plants, not just their held-out-flight rows; aggregation must happen after the split |
| Leave one year out | NIWO 2020↔2023 context | Remove repeated test plants from training; only one site supports this; not region-independent temporal validation |
| Leave one site out | Three directional spatial transfer experiments | Site-specific species mix and absent PFTs must be reported; folds are few and not random global sites |
| Leave one species out | Species transfer for PFTs having other training taxa | ECS cannot be learned when its sole species is held out; rare taxa give imprecise error estimates; leaving a species within the same site does not establish new-site transfer |

LOSO-species is a stronger empirical check of a transferable PFT pattern than an unidentified fixed-effect formula, but it is a prediction/generalization check, not a causal isolation of PFT from taxonomy. It is feasible for selected DBS/DBT/ECT taxa and limited EBS contexts; it is impossible as a complete five-class validation with the present ECS species replication. It is not performed or claimed by this audit's association tests.

## Future sampling

Add independently sampled taxa for ECS and EBS across multiple shared sites and acquisitions; balance crown/size/illumination conditions; measure individual traits rather than infer all PFTs from names; retain spatial coordinates and field identity reconciliation; sample the same species at several independent sites/years. This would improve the design more than fitting a more elaborate model to current aliases.
