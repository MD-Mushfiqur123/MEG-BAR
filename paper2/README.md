# Paper 2 — 3D Structural Pocket Grounding

Sequel to Paper 1 (MEG-BAR, JCIM submission `ci-2026-04206a`).

**Question:** Paper 1 measured that 1D sequence embeddings (ESM-2) cannot distinguish
the true orthosteric pocket from a wrong one. Does explicit 3D pocket geometry
(crystal or predicted structures) change that?

**Master plan:** see [`../PLAN_PAPER2_3D_GROUNDING_2026-11-13.md`](../PLAN_PAPER2_3D_GROUNDING_2026-11-13.md)
(41 phases, Stages 0–8).

## Status

| Stage | Phases | Status |
|---|---|---|
| 0 — Foundation | 1–4 | Phases 1–4 done |
| 1 — Structure data | 5–10 | complete (Phases 5–10 done) |
| 2 — 3D features | 11–15 | complete (Phases 11–15 done; 208 validation checks green) |
| 3 — Models (incl. wrong-pocket-3D control) | 16–21 | complete (all 6 arms measured; Arm A regression guard PASS; C vs E: +0.0003, p = 0.22 — decisive negative, see plan) |
| 4 — Evaluation | 22–26 | pending |
| 5 — Robustness | 27–31 | pending |
| 6 — Analysis & figures | 32–34 | pending |
| 7 — Manuscript | 35–38 | pending |
| 8 — Packaging & submission | 39–41 | pending |

## Directory layout

```
paper2/
  data/                    frozen inputs inherited from ../data/real/
  data/structures/         frozen structure artefacts (Phase 5-10)
    pdb_selection.json     reference structure selection (Phase 5)
    afdb/                  AlphaFold DB models + per-residue pLDDT (Phase 6)
    pockets_defined.json   orthosteric pockets, 6.5 A (Phase 7)
    residue_mapping.json   pocket -> UniProt -> ESM-2 token indices (Phase 8)
    pairs_41271.csv        frozen ChEMBL pairs joined onto structures (Phase 9)
    ligand_pair_mapping.json  pair coverage + exclusions (Phase 9)
    manifest.json          SHA-256 of every file here (Phase 10)
  data/features/           frozen 3D feature artefacts (Stage 2)
    {SYM}_distances.npz    CA + heavy-atom min distance matrices (Phase 11)
    {SYM}_contacts.npz     binary 4/6/8 A + weighted contact maps (Phase 12)
    {SYM}_graph.npz        pocket graphs: ESM-2 + one-hot + pLDDT nodes (Phase 13)
    {SYM}_geometry.npz     per-residue SASA (Phase 14)
    feature_validation.json  208 sanity checks (Phase 15)
  scripts/                 numbered, one phase per script where possible
    mmcif_lite.py          stdlib mmCIF parser + NW alignment (shared)
    stage2_common.py       pocket context loader (shared Stage 2)
    stage3_common.py       arms data/models/training + resume store (shared Stage 3)
    stage5_common.py       AFDB + radius-sweep pocket context builders (shared Stage 5)
    16..21_arm_*.py        the six model arms (A replication, B 1D, C 3D,
                           D distance-bias, E wrong-pocket-3D, F shuffled)
    22..26_*.py            Stage 4: scaffold master, temporal protocol,
                           low-resource guard, statistics, compute budget
    27..31_*.py            Stage 5: crystal-vs-AF, radius sweep, mutation
                           probe, variance decomposition, hypothesis verdicts
    run_stage1.py          Stage 1 orchestrator (checkpointed)
    run_stage2.py          Stage 2 orchestrator (checkpointed)
    run_stage3.py          Stage 3 orchestrator (checkpointed + report)
    run_stage4.py          Stage 4 orchestrator (checkpointed)
    run_stage5.py          Stage 5 orchestrator (checkpointed)
  results/                 frozen evaluation outputs + pipeline_state.json
  results/stage3/          arms_scaffold_results.json (granular-resume store,
                           all 7 arms x 11 receptors x 5 seeds) + report
  results/stage4/          scaffold_master, temporal_results, statistics,
                           low_resource, compute_budget
  results/stage5/          af_results + af_comparison, radius_sweep,
                           mutation_probe, variance_decomposition,
                           hypothesis_verdicts
  figures/                 300 DPI regenerable figures
  PREREGISTRATION.md       hypotheses H1-H4 + decision rules (Phase 4, frozen)
  ENVIRONMENT.md           verified versions + structure-tooling plan (Phase 3)
  DEFECT_REGISTER.md       failed claims, catalogued honestly
```

## Workflow automation

Stage 1 runs end-to-end with one command from the repo root:

```
make paper2-stage1            # runs phases 06 -> 07 -> 08 -> 09 -> 10, skips completed
make paper2-stage1-force      # rerun everything
make paper2-stage2            # runs phases 11 -> 12 -> 13 -> 14 -> 15 -> 10
make paper2-stage2-force      # rerun everything
make paper2-stage3            # runs phases 16 -> 21 (six arms) + report
make paper2-stage3-force      # delete the Stage 3 store and rerun all arms
make paper2-stage4            # runs phases 22 -> 26 (master table, temporal,
                              # low-resource, statistics, compute budget)
make paper2-stage4-force      # rerun all Stage 4 phases
make paper2-stage5            # runs phases 27 -> 31 (crystal-vs-AF, radius
                              # sweep, mutation probe, variance, verdicts)
make paper2-stage5-force      # rerun all Stage 5 phases
make paper2-test              # Paper 2 artefact tests only
make test                     # full suite
```

## Stage 7-8: manuscript, preprint, submission

```
paper2/manuscript/main.tex   full manuscript (compiles with Tectonic,
                             9 pp, zero undefined references)
paper2/manuscript/main.pdf   compiled manuscript
paper2/PREPRINT_PACKAGING.md Phase 40 checklist: Figshare / Zenodo /
                             GitHub release v3.0.0, in order
paper2/RELEASE_NOTES_v3.0.0.md  release notes text
paper2/submission/COVER_LETTER.md   Phase 41 cover letter + checklist
paper2/submission/toc_graphic.png   ACS TOC graphic, 3.25x1.75 in, 300 DPI
```

Regenerate the TOC graphic with
`python3 paper2/scripts/35_toc_graphic.py` (reads the frozen statistics
artefact; no numbers are hard-coded).

## Non-negotiables

1. Zero simulation; measured or explicitly "not run".
2. The wrong-pocket-3D control lands in the same commit as the first 3D model.
3. Null results are findings, not failures.
