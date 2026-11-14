# Paper 2 Master Plan — 3D Structural Pocket Grounding vs 1D Sequence Embeddings

**Working title:** *Does 3D Pocket Geometry Beat Wrong-Pocket Controls? Testing Structural Grounding of Protein Foundation Model Representations on 41,271 Measured ChEMBL Pairs*

**Date:** 2026-11-13 (v2 — expanded phase detail)
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

Each phase below lists: **Objective → Tasks → Inputs → Outputs → Exit criteria → Risks.**
A phase is "done" only when its exit criteria pass and its outputs are committed.

---

## Stage 0 — Foundation (Phases 1–4)

### Phase 1 — Charter
- **Objective:** freeze the scientific scope so nothing drifts later.
- **Tasks:** commit this plan; fix the receptor set (11 from Paper 1, no new families); fix the data source (Paper 1's frozen artefacts only); fix the central question and success criterion; record the companion-paper linkage.
- **Inputs:** Paper 1 manuscript, `data/real/` artefacts, PREREGISTRATION draft.
- **Outputs:** this file (v1).
- **Exit criteria:** plan merged; scope sentence appears verbatim in pre-registration.
- **Risks:** scope creep (new receptors, new datasets) — rejected by rule; any addition requires a dated amendment note here.

### Phase 2 — Repo scaffolding
- **Objective:** give every later phase a fixed home.
- **Tasks:** create `paper2/{data,scripts,results,figures}`; write `paper2/README.md` with stage/phase status table; decide the numbering convention for scripts (`paper2/scripts/NN_name.py`, matching Paper 1's `colab/scripts/` style); extend CI to lint paper2 scripts (syntax + import check) without running the heavy jobs.
- **Inputs:** repo layout conventions from Paper 1.
- **Outputs:** `paper2/` tree + README (done).
- **Exit criteria:** `pytest tests/` still green; README status table matches reality.
- **Risks:** CI runtime explosion from heavy scripts — mitigated by keeping CI to syntax/import checks and small unit tests only.

### Phase 3 — Environment lock
- **Objective:** make every number reproducible bit-for-bit.
- **Tasks:** verify installed versions (numpy 2.5.4, pandas 3.1.1, scipy 1.18.1, scikit-learn 1.9.1, torch 2.15.0+cpu, transformers 5.22.2, rdkit 2026.9.2, requests 2.34.2, matplotlib 3.11.2); plan structure tooling (biopython >= 7.8, prody >= 2.4, MDAnalysis fallback) to be added with Phase 5; list Paper 1 frozen artefacts Paper 2 must consume as-is; record CPU-only compute statement.
- **Inputs:** sandbox environment, Paper 1 requirements files.
- **Outputs:** `paper2/ENVIRONMENT.md` (done).
- **Exit criteria:** every package version recorded; frozen-input list complete; no undocumented dependency.
- **Risks:** prody/MDAnalysis build issues on some CI platforms — mitigated by adding them only when first needed and keeping a pure-numpy fallback for distance matrices/contact maps.

### Phase 4 — Pre-registration
- **Objective:** fix hypotheses and statistics before any structure is touched.
- **Tasks:** write the fixed 11-receptor table with UniProt accessions; write hypotheses H1–H4; define the primary endpoint (Arm C vs Arm E, paired Wilcoxon across 5 seeds, 95% bootstrap CI, Holm correction); define secondary endpoints (temporal split, low-resource, radius sweep); define decision rules including the negative-result path; declare the no-amendment rule (dated notes only).
- **Inputs:** Paper 1 results, this plan.
- **Outputs:** `paper2/PREREGISTRATION.md` (done, frozen).
- **Exit criteria:** file committed before Phase 5's first download; hypotheses and tests match this plan verbatim.
- **Risks:** temptation to "adjust" endpoints after seeing results — blocked by the no-amendment rule and by quoting the pre-registration verbatim in the manuscript.

---

## Stage 1 — Structure Data (Phases 5–10)

### Phase 5 — PDB mapping
- **Objective:** one reference crystal/cryo-EM structure per receptor (holo preferred, apo as secondary).
- **Tasks:** query RCSB search API per UniProt accession (P14416, P35462, P08908, P28223, P11229, P08913, P07550, P35367, P14867, P31645, Q01959); rank candidate structures by (a) resolution, (b) presence of co-crystallized orthosteric ligand, (c) species = Homo sapiens, (d) no large truncations; record PDB ID, method (X-ray/cryo-EM), resolution (A), co-crystallized ligand 3-letter code, chain ID, UniProt isoform match; write `paper2/scripts/05_pdb_mapping.py` so the search is re-runnable.
- **Inputs:** UniProt accessions from PREREGISTRATION.
- **Outputs:** `paper2/data/structures/pdb_selection.json` (per-receptor: primary + fallback PDB IDs with metadata).
- **Exit criteria:** every one of the 11 receptors has >= 1 candidate; choices documented with reasons; GPCR class-A receptors prefer active-state or antagonist-stabilized structures consistently (state choice recorded).
- **Risks:** SERT/DAT (SLC6 family) have fewer ligand-bound structures — accept antidepressant-bound structures and document; GABRA1 is a pentamer — define which subunit/chain is used and freeze it.

### Phase 6 — AlphaFold models
- **Objective:** predicted-structure comparison arm for every receptor.
- **Tasks:** download AFDB structures (AlphaFold monomer v2.5+) for all 11 accessions via the AFDB API; record model version, per-residue pLDDT; store alongside PDB entries.
- **Inputs:** UniProt accessions.
- **Outputs:** `paper2/data/structures/afdb/` + entries in the manifest.
- **Exit criteria:** 11/11 AFDB models downloaded; pLDDT profiles saved as arrays.
- **Risks:** AF models of flexible loops have low pLDDT — pocket-region pLDDT is what matters; record it and use it later in Phase 27.

### Phase 7 — Pocket definition
- **Objective:** a frozen, literature-defensible orthosteric pocket for each receptor.
- **Tasks:** define pocket as residues with any heavy atom within 6.5 A of the co-crystallized ligand; cross-check against UniProt binding-site annotations (already in `data/real/pockets*.json`) and literature anchors (Asp3.32 in aminergic GPCRs — DRD2 Asp114, DRD3 Asp110, HTR1A Asp82, HTR2A Asp155, CHRM1 Asp105, ADRB2 Asp113, HRH1 Asp107, ADRA2A Asp113); reconcile discrepancies by keeping the union and flagging differences; freeze the radius at 6.5 A for the main protocol (5.0/8.0 A saved for the Phase 28 sweep).
- **Inputs:** PDB structures (Phase 5), UniProt annotations (Paper 1 artefacts).
- **Outputs:** `paper2/data/structures/pockets.json` (per receptor: residue numbers, Ballesteros–Weinstein labels where applicable, anchor residues).
- **Exit criteria:** every receptor's pocket contains its literature anchor residue; pocket sizes (residue counts) recorded and sane (typically 20–45 residues for class-A GPCRs).
- **Risks:** ligand-bound states differ from the state relevant to some ligands — documented as a limitation; alternative-state sensitivity deferred to the radius sweep and discussion.

### Phase 8 — Sequence-structure alignment
- **Objective:** map every pocket residue onto the exact ESM-2 token index used in Paper 1.
- **Tasks:** align PDB SEQRES / ATOM records to the UniProt sequence stored in `proteins_expanded.json` (BioPython pairwise or SIFTS mapping); handle gaps, point mutations in constructs, and tags; produce per-receptor mapping tables `(PDB resnum, UniProt pos, ESM-2 token idx)`; assert every pocket residue maps — zero unmapped, else fail loudly.
- **Inputs:** Phase 5/7 outputs, `proteins_expanded.json` sequences.
- **Outputs:** `paper2/data/structures/residue_mapping.json`.
- **Exit criteria:** automated assertion: 0 unmapped pocket residues across 11 receptors; spot-check 5 residues per receptor by hand.
- **Risks:** construct mutations in crystal structures (common in stabilised GPCR constructs) — map to UniProt numbering, exclude non-mapping engineered residues, and document exclusions per receptor.

### Phase 9 — Ligand–pair mapping
- **Objective:** attach the 41,271 frozen pairs onto structures with full accounting.
- **Tasks:** load Paper 1's frozen pair tables; join by receptor symbol; record per-receptor pair counts carried forward; document exclusions (none expected — structures are per-receptor, not per-ligand); verify totals sum to 41,271 exactly.
- **Inputs:** `data/real/` frozen artefacts, receptor symbols.
- **Outputs:** `paper2/data/pairs_index.json`.
- **Exit criteria:** sum of per-receptor pairs == 41,271; checksum of source artefacts recorded.
- **Risks:** accidental re-curation — forbidden; this phase only reads frozen files.

### Phase 10 — Frozen structure artefacts
- **Objective:** make Stage 1 bit-reproducible.
- **Tasks:** SHA-256 every downloaded file (PDB/mmCIF, AFDB); write `paper2/data/structures/manifest.json` (file, sha256, source URL, download timestamp, phase); add a pytest that re-verifies checksums.
- **Inputs:** all Stage 1 downloads.
- **Outputs:** manifest + test.
- **Exit criteria:** manifest complete; test passes in CI.
- **Risks:** upstream files changing at source — mitigated because we hash what we stored, and the manifest documents provenance.

---

## Stage 2 — 3D Feature Engineering (Phases 11–15)

### Phase 11 — Distance matrices
- **Objective:** the core geometric representation.
- **Tasks:** per receptor, compute C-alpha pairwise distance matrix over the pocket; also heavy-atom minimum-distance matrix (residue x residue); store as `.npz` with residue-index metadata aligned to Phase 8 mapping; pure-numpy implementation (no heavy dependency needed).
- **Inputs:** Phase 7/8 outputs.
- **Outputs:** `paper2/data/features/distances_{crystal,afdb}.npz`.
- **Exit criteria:** matrices symmetric, zero diagonal, units Angstrom; shapes match pocket sizes; crystal vs AF difference quantified (mean |Δd|) and saved.
- **Risks:** coordinate frame differences between structures — irrelevant for intra-pocket distances (frame-free representation).

### Phase 12 — Contact maps
- **Objective:** discretized geometry for robustness analyses.
- **Tasks:** binary contact maps at 4/6/8 A; weighted contacts (exp(-d/d0)); store alongside distance matrices.
- **Inputs:** Phase 11 outputs.
- **Outputs:** `paper2/data/features/contacts_{crystal,afdb}.npz`.
- **Exit criteria:** contact counts at 6 A plausible vs literature pocket sizes; thresholds recorded in manifest.
- **Risks:** none serious; cheap phase.

### Phase 13 — Pocket graphs
- **Objective:** the model-ready representation (Arm C/D input).
- **Tasks:** build per-receptor pocket graphs: nodes = pocket residues carrying (a) ESM-2 per-residue embeddings from Paper 1's frozen `protein_embeddings*.npz` at the Phase 8 token indices, (b) residue identity one-hot; edges = k-nearest or distance-thresholded with edge features (distance, contact weight); store as PyG `Data` objects (torch_geometric) or a pure-torch fallback if PyG proves heavy for CI.
- **Inputs:** Phases 8, 11, 12 + Paper 1 embeddings.
- **Outputs:** `paper2/data/features/pocket_graphs.pt` (+ loader script).
- **Exit criteria:** node feature dims documented; graph connectivity checked (no isolated nodes at the chosen threshold); loader round-trips.
- **Risks:** PyG install weight in CI — fallback to a documented pure-torch edge-index format is acceptable and pre-decided here.

### Phase 14 — Geometric descriptors
- **Objective:** interpretable scalar features for analysis (and a sanity channel).
- **Tasks:** pocket volume/depth estimates (grid-based), residue SASA (FreeSASA algorithm or Shrake–Rupley in numpy), pocket sphericity; per-receptor descriptor table.
- **Inputs:** Phase 7 structures.
- **Outputs:** `paper2/data/features/descriptors.csv`.
- **Exit criteria:** descriptors in literature-plausible ranges; crystal vs AF comparison table.
- **Risks:** exact volume computation is tool-dependent — use one method consistently and document; descriptors are analysis aids, not model inputs (pre-decided to avoid degrees of freedom).

### Phase 15 — Feature validation
- **Objective:** prove the features are biologically real before modelling.
- **Tasks:** assert anchor residues present and correctly indexed; distance matrices symmetric + zero-diagonal; contact maps reproduce known disulfides (e.g., GPCR ECL disulfide Cys3.25–CysECL2 where present) and the TM bundle geometry (adjacent-TM contacts); compare crystal vs AF pocket RMSD; write all checks as pytest cases.
- **Inputs:** all Stage 2 outputs.
- **Outputs:** `paper2/scripts/15_validate_features.py` + passing tests.
- **Exit criteria:** every check green; any failure blocks Stage 3.
- **Risks:** a failed check here is a gift — it catches Stage 1/2 bugs before they contaminate results.

---

## Stage 3 — Models (Phases 16–21)

### Phase 16 — Arm A (replication guard)
- **Objective:** prove the harness reproduces Paper 1 exactly before adding anything new.
- **Tasks:** re-run Paper 1's shared model and Ridge-on-fingerprints on the identical frozen splits/seeds; compare to Paper 1's stored per-receptor numbers.
- **Inputs:** Paper 1 artefacts + harness code.
- **Outputs:** replication report `paper2/results/armA_replication.json`.
- **Exit criteria:** per-receptor r matches Paper 1 within float tolerance (same code path) or within documented tolerance if the harness was refactored; any mismatch blocks everything until explained.
- **Risks:** silent harness drift — this arm exists precisely to catch it.

### Phase 17 — Arm B (1D conditioning replication)
- **Objective:** reproduce Paper 1's cross-attention conditioning arm.
- **Tasks:** identical protocol to Arm A for the conditioning model; also re-run the wrong-pocket (1D) control from Paper 1.
- **Inputs:** same as Phase 16.
- **Outputs:** `paper2/results/armB_conditioning.json`.
- **Exit criteria:** reproduces Paper 1's headline (small, non-significant gains; wrong-pocket matches).
- **Risks:** as Phase 16.

### Phase 18 — Arm C (3D conditioning — hypothesis arm)
- **Objective:** the actual test of the paper.
- **Tasks:** pocket-graph encoder (GCN/GraphAttention or distance-biased attention over pocket residues) producing a pocket conditioning vector/key-value set fused with the ligand representation (Morgan FP + score head identical to Paper 1's shared model); trained with the same 5-seed scaffold-disjoint protocol; CPU-budget respected (small graphs, 20–45 nodes).
- **Inputs:** Phase 13 graphs, Paper 1 pair tables.
- **Outputs:** per-receptor metrics `paper2/results/armC_3d.json`.
- **Exit criteria:** runs complete on all 11 receptors (or minimum-data guard skips the sparse two, as in Paper 1); artefacts frozen.
- **Risks:** overfitting on small pockets — mitigated by parameter budget comparable to Paper 1's arms and by the 5-seed protocol.

### Phase 19 — Arm D (geometric bias attention)
- **Objective:** a second, architecturally different way to inject geometry.
- **Tasks:** relative-position/distance-bias attention where attention logits are biased by true pairwise pocket distances (like ALBERT/Transformer distance biases); same protocol as Arm C.
- **Inputs:** Phase 11 matrices + Phase 13 node features.
- **Outputs:** `paper2/results/armD_distbias.json`.
- **Exit criteria:** same as Phase 18.
- **Risks:** two hypothesis arms double the testing burden — Holm correction already covers the family; Arm D is secondary.

### Phase 20 — Arm E (wrong-pocket-3D control) — DECISIVE
- **Objective:** the control that decides the paper.
- **Tasks:** identical 3D pipeline as Arm C, but the pocket graph is built from a *wrong* receptor's structure (cyclically rotated receptor assignment, fixed mapping documented); same seeds/splits.
- **Inputs:** Phase 13 graphs (misassigned), pair tables.
- **Outputs:** `paper2/results/armE_wrongpocket3d.json`.
- **Exit criteria:** runs complete; artefact frozen; **lands in the same commit as Arm C** (non-negotiable).
- **Risks:** none scientific; this is the honest mirror.

### Phase 21 — Arm F (shuffled-coordinates control)
- **Objective:** separate geometry from residue identity.
- **Tasks:** true pocket residues, coordinates permuted across residues (fixed permutation per receptor, documented); identical pipeline.
- **Inputs:** Phase 13 graphs (shuffled), pair tables.
- **Outputs:** `paper2/results/armF_shuffled.json`.
- **Exit criteria:** same as Phase 20; same-commit rule applies.
- **Risks:** permutation choice is a degree of freedom — fix one deterministic permutation per receptor now, document it, never try alternatives (anti-fishing rule).

---

## Stage 4 — Evaluation (Phases 22–26)

### Phase 22 — Scaffold-disjoint protocol
- **Objective:** identical evaluation to Paper 1.
- **Tasks:** reuse Paper 1's frozen Bemis–Murcko splits and 5 seeds byte-for-byte; run Arms A–F; per-receptor Pearson r with 95% bootstrap CIs.
- **Outputs:** `paper2/results/scaffold_disjoint_master.json`.
- **Exit criteria:** Arm A/B numbers match Paper 1; all arms evaluated on identical folds.
- **Risks:** fold mismatch — prevented by consuming frozen split files, never regenerating.

### Phase 23 — Temporal protocol
- **Objective:** the deployment-realistic split.
- **Tasks:** train pre-2015, test 2015+ (Paper 1's frozen temporal definition); all arms.
- **Outputs:** `paper2/results/temporal_master.json`.
- **Exit criteria:** identical cut definition to Paper 1; all arms covered.
- **Risks:** fewer test pairs in some receptors — report per-receptor test sizes.

### Phase 24 — Low-resource protocol
- **Objective:** handle GABRA1/ADRA2A exactly as Paper 1 did.
- **Tasks:** minimum-data guard (skip cross-attention-style arms where data cannot support them); report Ridge-only where applicable; no silent substitution.
- **Outputs:** included in master tables with explicit "skipped (guard)" markers.
- **Exit criteria:** guard behaviour matches Paper 1's documented rule.
- **Risks:** temptation to squeeze a number out of sparse arms — blocked by rule.

### Phase 25 — Statistics
- **Objective:** the pre-registered inferential analysis.
- **Tasks:** primary endpoint (Arm C vs E, paired Wilcoxon across seeds, pooled data-rich receptors); per-receptor tests with Holm correction; bootstrap CIs (1,000 resamples, fixed seed); effect sizes (mean Δr with CI); write `paper2/scripts/25_statistics.py`.
- **Outputs:** `paper2/results/statistics.json` + human-readable summary.
- **Exit criteria:** exactly the tests pre-registered in PREREGISTRATION.md — no additions, no substitutions.
- **Risks:** multiple-comparison temptation — Holm fixed in advance.

### Phase 26 — Compute budget
- **Objective:** honest resource accounting.
- **Tasks:** record runtime per arm per receptor, total CPU-hours, peak memory; if any arm needed more, document what would be required on GPU.
- **Outputs:** `paper2/results/compute_budget.json`.
- **Exit criteria:** table complete; manuscript compute section can quote it directly.
- **Risks:** none; bookkeeping.

---

## Stage 5 — Robustness (Phases 27–31)

### Phase 27 — Crystal vs AF comparison
- **Objective:** does predicted-structure grounding behave like crystal grounding?
- **Tasks:** re-run Arm C with AFDB structures; compare per-receptor Δr vs crystal arm; correlate pocket pLDDT with agreement.
- **Outputs:** `paper2/results/crystal_vs_af.json`.
- **Exit criteria:** qualitative conclusion stability assessed and reported.
- **Risks:** AF pockets may miss water-mediated geometry — discussed, not fixed.

### Phase 28 — Pocket-radius sweep
- **Objective:** is the conclusion an artifact of 6.5 A?
- **Tasks:** re-define pockets at 5.0 and 8.0 A; re-run Arm C and E; compare.
- **Outputs:** `paper2/results/radius_sweep.json`.
- **Exit criteria:** conclusion (H2 supported or not) stable across radii, or the instability itself reported.
- **Risks:** three radii triple compute for two arms — acceptable on CPU given pocket sizes.

### Phase 29 — Mutation probe
- **Objective:** a mechanistic question 1D cannot answer.
- **Tasks:** select 2–3 point mutations with measured affinity shifts in ChEMBL (candidate: DRD2 point mutants; verify data availability first); compute mutant pockets/structures (rotamer-level or AF single-mutant where available); test whether 3D-grounded predictions track measured Δaffinity better than 1D.
- **Outputs:** `paper2/results/mutation_probe.json` + a pre-registered addendum note in PREREGISTRATION.md (dated) describing the exact mutants chosen and why, written before running.
- **Exit criteria:** mutants selected on data availability, not on results; zero post-hoc selection.
- **Risks:** mutant structure quality — use the most conservative available method and document; if infeasible, report as "not run" per the no-simulation rule.

### Phase 30 — Variance decomposition
- **Objective:** where does uncertainty live?
- **Tasks:** decompose variance of r into seed x split x receptor components for all arms.
- **Outputs:** `paper2/results/variance_decomposition.json`.
- **Exit criteria:** table complete; informs the manuscript's uncertainty discussion.
- **Risks:** none.

### Phase 31 — Negative-result guard
- **Objective:** protect the paper from outcome bias.
- **Tasks:** re-read PREREGISTRATION.md; write the results narrative for both outcomes (H2 supported / not supported) in skeleton form **before** looking at the statistics output; store both skeletons.
- **Outputs:** `paper2/results/narrative_skeletons/`.
- **Exit criteria:** both narratives drafted a priori; the final manuscript must be one of them (with numbers filled in).
- **Risks:** human drift — mitigated by committing both skeletons before Phase 25's output is examined.

---

## Stage 6 — Analysis & Figures (Phases 32–34)

### Phase 32 — Master result table
- **Objective:** one table to rule the manuscript.
- **Tasks:** all arms x 11 receptors x 2 splits, CI-annotated, script-generated (`paper2/scripts/32_master_table.py`); LaTeX output.
- **Exit criteria:** table regenerates from one command; numbers match the frozen JSONs.

### Phase 33 — Figures
- **Objective:** the visual story.
- **Tasks:** (a) pocket-graph schematic, (b) per-receptor Δr vs wrong-pocket-3D with CIs, (c) temporal decay across arms, (d) crystal-vs-AF agreement, (e) radius sweep; 300 DPI PNG + PDF; matplotlib only.
- **Exit criteria:** every figure regenerable; no manual edits.

### Phase 34 — Defect register
- **Objective:** honesty infrastructure.
- **Tasks:** create `paper2/DEFECT_REGISTER.md`; any failed claim, failed check, or protocol deviation gets a dated row; quote it in the manuscript appendix.
- **Exit criteria:** register exists even if empty (an empty register is itself a claim, verified by tests).

---

## Stage 7 — Manuscript (Phases 35–38)

### Phase 35 — Outline
- **Objective:** measured-first structure mirroring Paper 1.
- **Tasks:** sections: Intro → Related Work → Measured 3D Grounding Evaluation (main body) → Discussion → Conclusion → Appendices (method spec, proofs if any, defect register, reproducibility); reader's guide + evidentiary box.
- **Exit criteria:** outline committed; every planned table/figure mapped to a phase output.

### Phase 36 — Draft
- **Objective:** full text.
- **Tasks:** write Sections 1–5; every number cited to a frozen artefact; pre-registration quoted verbatim in the methods.
- **Exit criteria:** draft compiles; all `\cref` resolve.

### Phase 37 — Red-team review
- **Objective:** self-review at the Paper 1 reviewer's standard (62→95/100 rubric).
- **Tasks:** run the known failure modes checklist: title-claims-match-data, no simulated claims in main body, no dangling references, evidentiary table complete, controls prominent, limitations honest; fix everything found.
- **Exit criteria:** a dated red-team report file with every finding and its fix.

### Phase 38 — Reproducibility appendix
- **Objective:** complete audit trail.
- **Tasks:** environment, exact commands, artefact checksums, runtimes, machine specs.
- **Exit criteria:** a reader can re-run every number from the appendix alone.

---

## Stage 8 — Packaging & Submission (Phases 39–41)

### Phase 39 — Compile + verify
- **Tasks:** Tectonic build; zero undefined references; page count check; dangling-ref scan; pytest suite extended with paper2 artefact checks (checksums, master-table consistency).
- **Exit criteria:** all green in CI.

### Phase 40 — Preprint
- **Tasks:** Figshare deposit (same account, same ORCID); Zenodo deposit; repo release v3.0.0; `final/` updated with the Paper 2 PDF.
- **Exit criteria:** DOI minted; release published.

### Phase 41 — Journal submission
- **Tasks:** target JCIM (fast-lane conversation if Paper 1 is in revision there) or Journal of Cheminformatics as fallback; cover letter + TOC graphic (same pipeline as Paper 1); link Paper 1 as companion.
- **Exit criteria:** submission confirmed; manuscript ID recorded.

---

## Immediate Next Actions

- [x] Phase 1 — charter committed
- [x] Phase 2 — scaffolding
- [x] Phase 3 — environment lock
- [x] Phase 4 — pre-registration (frozen)
- [x] Phase 5 — PDB mapping (`paper2/scripts/05_pdb_mapping.py`) — 11/11 ligand-bound primaries, 2.17–3.14 A
- [ ] Phase 6 — AFDB models
- [ ] Phase 7 — pocket definition

## Non-Negotiables

1. Zero simulation. Zero fabricated numbers.
2. The wrong-pocket-3D control (Arm E) and shuffled-coordinates control (Arm F) land in the same commit as the first 3D model (Arm C) — never after.
3. Any deviation from this plan is documented in this file with a dated note — history is never rewritten.
4. Personal/academic-background details of the author are never part of any repo artefact, manuscript, or submission — the work speaks for itself.

## Amendment Log

- 2026-11-13 — v2: phases expanded with Objective/Tasks/Inputs/Outputs/Exit-criteria/Risks detail; no scientific content changed; Stage 0 marked complete (Phases 1–4).
