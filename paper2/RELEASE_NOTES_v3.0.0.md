# Release v3.0.0 — Paper 2: 3D Structural Pocket Grounding vs 1D Sequence Embeddings

Companion to Paper 1 (preprint DOI 10.6084/m9.figshare.35002837; JCIM
submission ci-2026-04206a).

## What is in this release

- **Complete measured pipeline** for the pre-registered question: does
  explicit 3D pocket geometry beat wrong-pocket / shuffled / 1D controls
  on 41,271 measured ChEMBL affinity pairs across 11 receptors?
- **Stages 0–8 artefacts**: structure manifests (SHA-256), 3D features,
  six model arms, two evaluation protocols, robustness suite, figures,
  and the full manuscript (`paper2/manuscript/main.pdf`).

## Headline measured results (all frozen, regenerable)

- H1 (C > B): +0.0172, p = 0.867 — NOT SUPPORTED
- H2 primary (C vs wrong-pocket-3D, scaffold-disjoint): +0.00025,
  p = 0.221, 95% CI [−0.022, +0.022] — NOT SUPPORTED
- Temporal protocol (E5): C vs E −0.0090, p = 0.041 (sign reversed) —
  NOT SUPPORTED
- H3 (C > shuffled): +0.0112, p = 0.156 — NOT SUPPORTED
- H4 (verdict transfer crystal → AlphaFold): SUPPORTED — pooled
  Δr = −0.00279, per-receptor |Δr| ≤ 0.016
- Radius sweep 5.0/6.5/8.0 Å: +0.022 / +0.0003 / +0.001, none significant
- Variance: receptor 84.5%, arm 2.7%, residual 12.8%
- Mutation probe: honestly not run (no mutant-identifying fields in the
  frozen artefacts); reason recorded in `paper2/results/stage5/mutation_probe.json`
- Compute: 2.34 h CPU-only, 280 trained models

## Reproduce

```
make paper2-stage1   # structures, pockets, mapping, manifest
make paper2-stage2   # distances, contacts, graphs, geometry
make paper2-stage3   # six arms, scaffold-disjoint
make paper2-stage4   # temporal, statistics, budget
make paper2-stage5   # crystal-vs-AF, radius sweep, verdicts
make paper2-test     # 69 artefact tests
```

## Integrity

- Zero simulation, zero fabricated numbers; every headline number traces
  to a frozen JSON artefact.
- Wrong-pocket-3D control landed in the same commit as the first 3D arm.
- All deviations catalogued in `paper2/DEFECT_REGISTER.md` (6 rows).
