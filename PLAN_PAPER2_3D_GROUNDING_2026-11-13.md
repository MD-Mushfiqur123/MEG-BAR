# Paper 2 Master Plan — 3D Structural Pocket Grounding vs 1D Sequence Embeddings

**Working title:** *Does 3D Pocket Geometry Beat Wrong-Pocket Controls? Testing Structural Grounding of Protein Foundation Model Representations on 41,271 Measured ChEMBL Pairs*

**Date:** 2026-11-13
**Author:** Md Mushfiqur Rahim (ORCID 0009-0003-1021-685X)
**Companion:** Paper 1 (JCIM submission ci-2026-04206a; preprint DOI 10.6084/m9.figshare.35002837)

## The Central Question

Paper 1 measured that cross-attention receptor conditioning adds small, statistically
insignificant gains (p >= 0.0625) that a wrong-pocket control reproduces — 1D sequence
embeddings (ESM-2) cannot distinguish the true orthosteric pocket from a wrong one.
**Paper 2 asks:** if explicit 3D pocket geometry (crystal structures from PDB, or
predicted structures) is added as grounding — distance matrices, contact maps, pocket
residue graphs — can any model finally beat the wrong-pocket control?

**Success criterion (pre-registered):** a 3D-grounded model significantly outperforms
the wrong-pocket-3D control under scaffold-disjoint and temporal splits. If it does not,
that is also a publishable, decisive negative result — the 1D-vs-3D question gets a
measured answer either way.

## Design Principles (inherited from Paper 1)

- Measured-first: every headline number comes from an executed run with a frozen artefact.
- Controls decide: wrong-pocket-3D, shuffled-coordinate, and sequence-only baselines are mandatory arms.
- No simulation: no parametric generators. If an experiment is not run, it is reported as not run.
- Defect register: any theoretical claim that fails is catalogued, never quietly dropped.
- All artefacts SHA-256-frozen; every figure regenerable from one command.

---

## Stage 0 — Foundation (Phases 1–4)

1. **Phase 1 — Charter:** commit this plan; freeze scope (11 receptors from Paper 1; no new families).
2. **Phase 2 — Repo scaffolding:** `paper2/` tree (data/, scripts/, results/, figures/); CI job extended.
3. **Phase 3 — Environment lock:** pin BioPython, ProDy/MDAnalysis, ESM-2, torch; record versions in `paper2/ENVIRONMENT.md`.
4. **Phase 4 — Pre-registration:** write hypotheses H1–H4, success criteria, and the exact statistical tests into `paper2/PREREGISTRATION.md` before any data work.

## Stage 1 — Structure Data (Phases 5–10)

5. **Phase 5 — PDB mapping:** for each of the 11 receptors, find reference crystal/cryo-EM structures (holo + apo); record PDB IDs, resolution, ligand co-crystallized.
6. **Phase 6 — AlphaFold models:** download AFDB predicted structures as the fallback/comparison arm for receptors without good crystals.
7. **Phase 7 — Pocket definition:** define orthosteric pockets per receptor from co-crystallized ligands (<= 6.5 A) + literature annotations (e.g., Asp3.32 anchor in aminergic GPCRs).
8. **Phase 8 — Sequence-structure alignment:** map each pocket residue onto the exact ESM-2 token indices used in Paper 1 (SIFTS/UniProt mapping); assert zero unmapped pocket residues.
9. **Phase 9 — Ligand–pair mapping:** join the 41,271 pairs from Paper 1's frozen artefacts onto receptor structures; document coverage and exclusions.
10. **Phase 10 — Frozen structure artefacts:** SHA-256 all PDB/mmCIF files; write `paper2/data/structures/manifest.json`.

## Stage 2 — 3D Feature Engineering (Phases 11–15)

11. **Phase 11 — Distance matrices:** C-alpha and heavy-atom pairwise distance matrices per pocket.
12. **Phase 12 — Contact maps:** binary + weighted contact maps at 4/6/8 A thresholds.
13. **Phase 13 — Pocket graphs:** residues as nodes (with ESM-2 embeddings), 3D distances as edges; store as PyG `Data` objects.
14. **Phase 14 — Geometric descriptors:** pocket volume, depth, sphericity, residue exposure (SASA) via ProDy/FreeSASA.
15. **Phase 15 — Feature validation:** sanity checks — pocket residues reproduce literature anchor residues; distance matrices symmetric; contact maps match known disulfides/salt bridges.

## Stage 3 — Models (Phases 16–21)

16. **Phase 16 — Arm A (replication):** Paper 1's shared model + Ridge-on-fingerprints baseline, re-run on the identical frozen splits (regression guard: numbers must reproduce).
17. **Phase 17 — Arm B (1D conditioning):** Paper 1's cross-attention receptor conditioning (exact reproduction).
18. **Phase 18 — Arm C (3D conditioning):** pocket-graph cross-attention or GNN encoder fused with ESM-2 embeddings — the actual hypothesis arm.
19. **Phase 19 — Arm D (geometric bias):** pocket-distance-bias attention (relative-position encoding from true coordinates).
20. **Phase 20 — Arm E (wrong-pocket-3D control):** identical 3D pipeline but pocket residues from a *wrong* receptor's structure — the decisive control.
21. **Phase 21 — Arm F (shuffled-coordinates control):** true pocket residues with permuted 3D coordinates — separates "geometry" from "residue identity".

## Stage 4 — Evaluation (Phases 22–26)

22. **Phase 22 — Scaffold-disjoint protocol:** identical to Paper 1 (Bemis–Murcko, 5 seeds, frozen splits).
23. **Phase 23 — Temporal protocol:** train pre-2015, test 2015+, identical to Paper 1.
24. **Phase 24 — Low-resource protocol:** GABA-A alpha1 and alpha2A sparse arms handled with the same minimum-data guard.
25. **Phase 25 — Statistics:** paired Wilcoxon across seeds (model vs wrong-pocket-3D), 95% bootstrap CIs, Holm correction across the 11 receptors.
26. **Phase 26 — Compute budget:** CPU-only feasibility check; if a GPU is required, document exactly what and why (honesty about resources).

## Stage 5 — Robustness (Phases 27–31)

27. **Phase 27 — Crystal-vs-AF comparison:** does predicted-structure grounding behave like crystal grounding? (practical relevance)
28. **Phase 28 — Pocket-radius sweep:** 5.0/6.5/8.0 A pocket definitions; is the conclusion stable?
29. **Phase 29 — Mutation probe:** 2–3 known resistance/point mutations (e.g., D2 point mutants with measured affinity shifts from ChEMBL) — does 3D grounding respond where 1D cannot?
30. **Phase 30 — Seed and split variance:** full variance decomposition (seed x split x receptor).
31. **Phase 31 — Negative-result guard:** pre-specify that null results on H1–H4 are reported as findings, not failures.

## Stage 6 — Analysis & Figures (Phases 32–34)

32. **Phase 32 — Result tables:** one master table (all arms x 11 receptors x 2 splits), CI-annotated, generated by script.
33. **Phase 33 — Figures:** pocket-graph schematic, per-receptor Delta-r vs control, temporal decay, crystal-vs-AF comparison. 300 DPI, regenerable.
34. **Phase 34 — Defect register:** any claim that failed gets a row in `paper2/DEFECT_REGISTER.md`.

## Stage 7 — Manuscript (Phases 35–38)

35. **Phase 35 — Outline + measured-first skeleton** (mirror Paper 1's structure: measurements in the main body, method spec in appendix).
36. **Phase 36 — Draft Sections 1–5** (Intro, Related Work, Measured Evaluation, Discussion, Conclusion).
37. **Phase 37 — Internal red-team review:** re-run the Paper 1 reviewer checklist (62→95/100 rubric) on the draft; fix everything.
38. **Phase 38 — Reproducibility appendix:** environment, exact commands, artefact checksums, runtime.

## Stage 8 — Packaging & Submission (Phases 39–41)

39. **Phase 39 — Compile + verify:** Tectonic build, zero undefined references, page count, dangling-ref scan, pytest suite extended to cover paper2 artefacts.
40. **Phase 40 — Preprint:** Figshare DOI (same account), Zenodo deposit, repo release v3.0.0.
41. **Phase 41 — Journal submission:** target JCIM (fast lane if Paper 1 is in revision there) or Journal of Cheminformatics; cover letter + TOC graphic; link Paper 1 as companion.

---

## Immediate Next Actions (Stage 0)

- [x] Phase 1 — this file committed
- [ ] Phase 2 — `paper2/` scaffolding
- [ ] Phase 3 — environment lock
- [ ] Phase 4 — pre-registration document

## Non-Negotiables

1. Zero simulation. Zero fabricated numbers.
2. The wrong-pocket-3D control runs in the same commit as the first 3D model — never after.
3. Any deviation from this plan is documented in the plan file itself with a dated note.
