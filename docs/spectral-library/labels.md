# Which labels should I use?

| System | Meaning and source | Appropriate use | Main limitation |
|---|---|---|---|
| Species | Recorded source taxonomy, sometimes absent or unresolved | Taxon summaries and composition checks | A populated name is not verified identification or an independent sample |
| Inferred PFT | Packaged species-to-functional-type crosswalk | Conditional comparisons of sampled functional groups | Species and PFT are confounded; unresolved taxa remain unassigned |
| Researcher `cover_category` | Five broad source-table classes chosen by researchers | Broad empirical cover comparisons | Includes nonliving and mixed materials; not a taxonomic PFT system |
| Physical material class | Independently justified endmember interpretation, ideally with purity/cover evidence | Mixture and abundance inference | Source cover labels alone do not certify material purity |

The five researcher categories in this library are **Deciduous**, **Evergreen**,
**Herbaceous**, **Non-vegetated & dead**, and **Woody shrub**. The inferred PFT
codes are DBS (deciduous broadleaf shrub), DBT (deciduous broadleaf tree), EBS
(evergreen broadleaf shrub), ECS (evergreen conifer shrub) and ECT (evergreen
conifer tree). These inferred groups cover woody taxa; they do not represent the
full herbaceous/background library.

The crosswalk is explicit and versioned at
`src/spectralbridge/data/plant_pft_crosswalk.csv`. Do not assign a missing species
by guessing from its cover category. A crosswalk assignment is an interpretation
of taxonomy, not a source researcher annotation.

**Non-vegetated & dead is not one physically coherent endmember class.** It can
contain bare, rock, dead standing/downed material and mixed annotations. Bare is
not verified pure soil. Mixed polygons are not validated pure endmembers.
Conservative material subclasses in the MESMA audit are diagnostic proxies,
not evidence of independent fractional-cover truth. Inconsistent or incomplete
subcategory labels remain explicit reconciliation tasks.

[Biological comparisons](biological-variation.md) keep these hierarchies separate.
The [MESMA readiness page](mesma-readiness.md) explains why additional material
coverage and independent purity/abundance observations are required.
