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
| 2 — 3D features | 11–15 | pending |
| 3 — Models (incl. wrong-pocket-3D control) | 16–21 | pending |
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
  scripts/                 numbered, one phase per script where possible
    mmcif_lite.py          stdlib mmCIF parser + NW alignment (shared)
    run_stage1.py          Stage 1 orchestrator (checkpointed)
  results/                 frozen evaluation outputs + pipeline_state.json
  figures/                 300 DPI regenerable figures
  PREREGISTRATION.md       hypotheses H1-H4 + decision rules (Phase 4, frozen)
  ENVIRONMENT.md           verified versions + structure-tooling plan (Phase 3)
  DEFECT_REGISTER.md       failed claims, catalogued honestly
```

## Workflow automation

Stage 1 runs end-to-end with one command from the repo root:

```
make paper2-stage1            # runs phases 06 -> 07 -> 08 -> 10, skips completed
make paper2-stage1-force      # rerun everything
make paper2-test              # Paper 2 artefact tests only
make test                     # full suite
```

## Non-negotiables

1. Zero simulation; measured or explicitly "not run".
2. The wrong-pocket-3D control lands in the same commit as the first 3D model.
3. Null results are findings, not failures.
