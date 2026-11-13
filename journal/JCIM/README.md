# JCIM Journal Version — Measured-Only Manuscript

This folder contains the **journal submission version** of the MEG-BAR
manuscript, prepared for *Journal of Chemical Information and Modeling*
(JCIM) or *Journal of Cheminformatics*.

## What differs from the preprint (`latex/main.tex`, 47 pages)

Per the pre-submission review advice, this version drops the simulation-only
design-study appendices (Design-Study Setup, Design-Study Results, Oncological
Kinase extension, Ablation Studies) so that referees read only the measured
work:

| | Preprint (`latex/`) | Journal version (this folder) |
|---|---|---|
| Pages | 47 | **30** |
| Main body (measured) | pp. 1–18 | pp. 1–16 |
| Simulation design study | Appendix C–F | **removed** (available in the companion preprint) |
| Theory appendices + proofs | kept | kept (the oncological-adapter invariance proposition and its mask definition are relocated into the theory appendix) |
| Defect register | kept | kept |
| Title / abstract / results | identical | identical (title: "Ligand Fingerprints, Not Expert Routing or Pocket Conditioning, Drive Cross-Family Affinity Prediction in Protein Foundation Models: A Controlled Study on 56,637 Measured ChEMBL Records") |

Every quantitative claim in both versions is the same measured number; nothing
was re-computed for this version. Sentences that referenced the removed
design-study sections were rewritten to point to the companion preprint.

## Build

```
tectonic -X compile main.tex
```

(Tectonic 0.17.0; 30 pages, no errors, no undefined references.)

## Files

- `main.tex` — journal-version source (single-file edits documented above)
- `real_eval.tex` — the measured-evaluation section (unchanged from the preprint)
- `references.bib`, `neurips.sty`, `neurips_2024.sty`, figure PNGs — unchanged
- `main.pdf` — compiled journal version

## Submission checklist

See `ARXIV_SUBMISSION_CHECKLIST.md` at the repository root for the shared
submission steps; for JCIM, additionally follow the ACS author guidelines
(word/figure limits, template choice) and note that the preprint remains
citable as the full version containing the simulation design study.
