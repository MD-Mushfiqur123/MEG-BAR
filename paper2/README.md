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
| 0 — Foundation | 1–4 | Phase 1 done; 2–4 pending |
| 1 — Structure data | 5–10 | pending |
| 2 — 3D features | 11–15 | pending |
| 3 — Models (incl. wrong-pocket-3D control) | 16–21 | pending |
| 4 — Evaluation | 22–26 | pending |
| 5 — Robustness | 27–31 | pending |
| 6 — Analysis & figures | 32–34 | pending |
| 7 — Manuscript | 35–38 | pending |
| 8 — Packaging & submission | 39–41 | pending |

## Directory layout (to be filled in Stage 0–1)

```
paper2/
  data/
    structures/     PDB/mmCIF artefacts + manifest.json (SHA-256 frozen)
  scripts/          numbered, one phase per script where possible
  results/          frozen evaluation outputs
  figures/          300 DPI regenerable figures
  PREREGISTRATION.md   hypotheses H1-H4 + statistical tests (Phase 4)
  ENVIRONMENT.md       pinned versions (Phase 3)
  DEFECT_REGISTER.md   failed claims, catalogued honestly (Phase 34)
```

## Non-negotiables

1. Zero simulation; measured or explicitly "not run".
2. The wrong-pocket-3D control lands in the same commit as the first 3D model.
3. Null results are findings, not failures.
