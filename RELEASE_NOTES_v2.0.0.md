# Release Notes — v2.0.0 (Measured Evidence Base)

**Tag:** `v2.0.0` (create after PR #3 merges to `main`)
**Date:** 2026-11-13

## Headline

This release replaces the manuscript's simulated accuracy claims with a fully
measured evidence base: real ChEMBL data, a genuine frozen ESM-2 650M
checkpoint, multi-seed statistics, and three decisive controls. The paper's
core claim is now a controlled negative result.

## Measurement (real experiments)

- **Eleven human receptors** (DRD2, DRD3, HTR1A, HTR2A, CHRM1, GABRA1,
  ADRA2A, ADRB2, HRH1, SLC6A3/DAT, SLC6A4/SERT): 56,637 measured
  Ki/IC50/Kd records from ChEMBL, 41,271 unique receptor–ligand pairs.
  Human DAT accession corrected: Q01959 (CHEMBL238); the plan document's
  P23975 is NET (SLC6A2) — correction documented in `data/real/expand_manifest.json`.
- **Five-seed protocol** with Bemis–Murcko scaffold-disjoint splits: Pearson
  r = 0.50–0.80 for the ten data-rich receptors; the simulated 0.834 is
  withdrawn.
- **Temporal split** (train pre-2015, test 2015+): shared-model r = 0.11–0.72;
  the negative conclusion survives both split designs.
- **Three controls, all negative for the architecture:** (1) trained router
  stays near-uniform (gate entropy ≥ 93% of max) and never beats a
  frozen-uniform router; (2) cross-attention receptor conditioning is never
  significantly better (paired Wilcoxon, p ≥ 0.0625) and the wrong-pocket
  control matches it; (3) Ridge on Morgan fingerprints alone is competitive
  throughout (r = 0.39–0.83) and is the only model with signal on GABRA1
  (r = 0.53 vs ≈ 0.01 for the deep models).

## Physicochemical profiling and hERG liability (computed, replaces fabricated constants)

- RDKit descriptors on all 14,425 unique molecules; CNS-MPO(4) = 2.62 ± 0.77
  (pKa/cLogD terms omitted and labelled); Veber 93.2%, Lipinski 71.2%.
- The fabricated BBB-penetration claim (CNS-MPO 5.24/6.0, 96.4% compliance)
  is withdrawn.
- hERG (CHEMBL240) QSAR: 9,628 molecules, scaffold-disjoint logistic
  regression, ROC-AUC 0.729 [0.706, 0.753].

## Packaging

- `requirements.txt` (core, bounded ranges for CI) and `requirements_colab.txt`
  (exact pins of the environment that produced every frozen artefact).
- `scripts/one_click_reproduce.py`: one-command reproduction, 8 stages.
- Zenodo metadata and arXiv submission manifest regenerated from the measured
  manuscript and regression-checked (`scripts/verify_zenodo_metadata.py`).
- `ARXIV_SUBMISSION_CHECKLIST.md` (incl. venue recommendation for a negative
  result) and `MENTORSHIP_OUTREACH_EMAIL.md`.
- 23-test verification suite; CI matrix 3 OS × Python 3.10/3.11/3.12.

## Honesty guarantees retained

- No sentence without measurement support; the 0.834/0.812 simulated numbers
  are not restored anywhere.
- The GABA-A divergence is reported whether or not it flatters the paper.
- Simulation-only sections are retained only as a labelled design study; all
  withdrawn claims are catalogued in the defect register.
