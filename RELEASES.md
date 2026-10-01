# Release packaging

The Git repository intentionally excludes binary result ZIP bundles.

For the initial rescue-service publication, a natural GitHub Release is:

- tag: `raddningstjanst-v0.2`
- release asset: `raddningstjanst-publication-package-v0.2.zip`
- source-package SHA-256:
  `1dfc519cff9ba8d2e86547dbc91aff21e84df244020b5fae088ed74072aba595`

The release description should point readers to:

- `evidence-matrix/Evidence-Matrix-v0.2.md`
- `raddningstjanst/synthesis/Raddningstjanst-Cross-Branch-Causal-Synthesis-v0.1.md`
- the two study directories under `raddningstjanst/`.

This keeps binary archives out of Git history while preserving a frozen,
downloadable publication package.
