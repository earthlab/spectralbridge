# SpectralBridge Documentation Style Guide

This guide establishes conventions for writing documentation in the SpectralBridge project. Its goal is to create a linear, pedagogical narrative that makes the package easy to understand and adopt. Use "SpectralBridge" for the package or project name, and use "cross-sensor calibration" when referring to the technical workflow or scientific concept.

## Philosophy
- **Clarity first.** Explain concepts in plain language before introducing technical jargon.
- **Narrative flow.** Documentation should guide the reader from inputs through processing to outputs in a logical order.
- **Pragmatic examples.** Every section should include code snippets or workflows that users can run directly.
- **Minimal prerequisites.** Link to background materials rather than assuming extensive prior knowledge.

## Information architecture

- **Learn** contains task-oriented educational material. Maintain one canonical
  vignette for each user-facing workflow module, plus the full-pipeline and
  restart/resume vignettes.
- **Validation** contains generated evidence from recorded input-variation
  campaigns. Maintain one page per validated module, preserve failures and
  skips, and distinguish synthetic contracts from live scientific evidence.
- **Technical reference** contains stage contracts, interfaces, filenames,
  schemas, algorithms, runtime, and architecture descriptions.
- **Project** contains contributor, release, citation, publication, and
  transparency material.
- Preserve old URLs when consolidating pages, but remove superseded tutorials
  from navigation and search so readers encounter one canonical learning path.

## Validation page structure

1. **Evidence boundary** – State whether inputs are synthetic, already present,
   or downloaded live and what claims the campaign can support.
2. **Input matrix** – Show every variation and its relevant parameters.
3. **Observed diagnostics** – Report quantitative results, not only pass/fail.
4. **Explicit checks** – Name each tested invariant and preserve failures and
   skip reasons.
5. **QA implications** – Explain how the diagnostics may improve QA without
   changing scientific thresholds before representative real-data review.
6. **Reproduction** – Link the machine-readable record and exact runner command.

## Vignette structure

1. **Purpose** – State when to use the module and how it fits the workflow.
2. **Prerequisites** – List required data, dependencies, and completed stages.
3. **Runnable example** – Present the smallest supported entry point.
4. **Success evidence** – Name the files or metrics that prove it worked.
5. **Next steps** – Link to the next vignette and deeper technical reference.

## Style
- Use Markdown headings (`#`, `##`, `###`) to organize content.
- Write in the second person (“you”) and active voice.
- Keep sentences concise; aim for one idea per sentence.
- Use numbered lists for sequences and bullet lists for options.
- Highlight file names, parameters, and code using backticks (`like_this`).
- Wrap code examples in fenced blocks with the appropriate language tag.
- Include diagrams or figures when they clarify complex processes.
- Cross-link related documents with relative paths.

## Formatting
- Line length: soft wrap at 100 characters.
- Use American English spelling.
- Date format: YYYY-MM-DD.
- Reference issues or pull requests with full links.

## Maintenance
- Each documentation page must include a `Last updated: YYYY-MM-DD` line at the end.
- When updating docs, ensure examples are tested against the current codebase.
- Run `pytest` before committing changes that affect code examples.

Following this guide will keep the documentation consistent and approachable for new contributors and users.
