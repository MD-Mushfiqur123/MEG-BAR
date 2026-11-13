# arXiv Submission Checklist — MEG-BAR

Manuscript: "Ligand Fingerprints, Not Expert Routing or Pocket Conditioning,
Drive Cross-Family Affinity Prediction in Protein Foundation Models: A
Controlled Study on 56,637 Measured ChEMBL Records"

All metadata lives in `arxiv_submission_manifest.json` and is validated by
`scripts/verify_zenodo_metadata.py` (run it before every submission attempt).

## 1. Before compiling

- [ ] LaTeX toolchain available (Overleaf, or TeX Live 2024+ locally). This
      repository's PDF has been compiled with Tectonic 0.17.0 (47 pages) — `scripts/check_latex_build.py`
      passes all 7 sanity modules, but the page count must be confirmed.
- [x] Compiled with Tectonic 0.17.0: **47 pages**, no errors, no undefined references (2026-11-13).
- [ ] Confirm the final page/figure/table counts and update the `comments`
      field of `arxiv_submission_manifest.json` if they differ from
      "47 pages, 8 figures, 19 tables" (measured by compiling with Tectonic 0.17.0; the verify script asserts these strings;
      update both places together).

## 2. Package the arXiv source tarball

- [ ] Build the submission bundle: `python scripts/package_deliverables.py`
      (produces `deliverables/MEG-BAR_Overleaf.zip`).
- [ ] arXiv wants a single `.tar.gz` of the LaTeX source: include `main.tex`,
      `real_eval.tex` (and any other `\input`ed files), `references.bib`,
      `neurips.sty`, `neurips_2024.sty`, and every figure file referenced by
      `\includegraphics`. The compiled `.bbl` must be included (arXiv does not
      run BibTeX for all styles).
- [ ] Test-compile the tarball exactly as arXiv will (no shell-escape, no
      network access).

## 3. Submit

- [ ] License: CC BY 4.0 (already set in the manifest).
- [ ] Primary category: `q-bio.BM`; secondaries: `cs.LG`, `q-bio.QM`.
- [ ] Author: Md Mushfiqur Rahim (ORCID 0009-0003-1021-685X). arXiv requires
      endorsement for a new subcategory — request endorsement well in advance.
- [ ] Paste the abstract from `arxiv_submission_manifest.json` verbatim (it is
      generated from `latex/main.tex` and regression-checked for withdrawn claims).
- [ ] After arXiv assignment, add the arXiv ID to `zenodo_metadata.json`
      related identifiers and to `README.md`.

## 4. Venue recommendation (result strength: negative result)

The measured result is a rigorous negative/deflationary result. Per the
publication plan, target a venue that values careful measurement over novelty
claims:

1. **Workshops (fastest, best fit):** NeurIPS/ICML workshop on
   *Machine Learning for Drug Discovery* or *Reproducibility in ML*
   (e.g. ML4Molecules, RE-FIG). A controlled negative result with public
   artefacts is exactly what reproducibility workshops want.
2. **Journals:** *Bioinformatics* (application note + full paper),
   *Journal of Chemical Information and Modeling*, or *PLOS ONE*
   (registered/reporting-friendly).
3. **Avoid** headline venues (Nature Biotechnology, NeurIPS main track):
   the paper itself documents that its earlier simulated claims were withdrawn;
   the honest contribution is the negative result and the defect register.

## 5. Zenodo archive

- [ ] Upload the frozen `data/real/` artefacts + scripts + compiled PDF to
      Zenodo using `zenodo_metadata.json` (validated by the verify script).
- [ ] Record the Zenodo DOI in `README.md` and cite it in the manuscript's
      data-availability statement.
