# CI ownership and publication gates

| Workflow | Responsibility | Publishes? |
| --- | --- | --- |
| `ci.yml` | Lint, lite/full package tests, AI and validation-source consistency | No |
| `docs.yml` | Reusable documentation check: generated records, JOSS structure, internal links, strict build, browser smoke and verified site artifact | No |
| `gh-pages.yml` | Calls docs checks, packages that exact verified artifact and deploys through the official GitHub Pages artifact flow | Website only |
| `joss-paper.yml` | Canonical `paper/` source checks and pinned official JOSS PDF build | CI preview artifact only |
| `docs-drift.yml` | Heuristic source/documentation drift audit; reports critical missing contract mentions | No |
| `qa-ci.yml` | Bounded QA fixture/test slice and rendered diagnostic artifact | No |
| `release.yml` | Source/docs/metadata gates, build once, exact wheel/sdist smoke, release and protected trusted PyPI publishing | Gated software release |

There is one website deployment owner. Documentation checks run on pull requests
and are called before main-branch deployment. They upload the built bytes; Pages
publishes those verified bytes rather than rebuilding in a second workflow.
GitHub Pages must be configured to use GitHub Actions, with the existing protected
`github-pages` environment. Confirm those external repository settings before
first deployment after migration.

Local checks do not prove that remote Actions or protected publisher environments
are configured correctly. No remote deployment or release is performed by the
cleanup. Synthetic software/browser tests are not scientific validation.

## Deterministic and external checks

Internal paths, anchors, assets, source fingerprints and generated records are
required checks and work offline after dependencies are installed. Browser smoke
checks representative pages at desktop/mobile widths, local assets and search.
External DOI/publisher/website availability is best-effort; network instability
must not block a software release or be confused with missing scientific evidence.
Run a manual external link check when preparing the actual submission.

`tools/site_prepare.py` is a legacy diagnostic helper. CI does not use it to copy
a temporary drift report into the public documentation. `docs-drift.yml` retains
the audit as a separate heuristic whose outputs are an artifact, not a tutorial.
