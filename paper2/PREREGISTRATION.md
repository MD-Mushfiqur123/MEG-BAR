# Paper 2 — Pre-Registration (Phase 4)

Written: 2026-11-13, **before** any structure download, feature computation, or model
training for Paper 2. This file is frozen at commit time; later edits append dated
notes, never rewrite history.

## Receptors (fixed set, inherited from Paper 1)

| Symbol | UniProt | Name |
|---|---|---|
| DRD2 | P14416 | Dopamine D2 receptor |
| DRD3 | P35462 | Dopamine D3 receptor |
| HTR1A | P08908 | Serotonin 5-HT1A receptor |
| HTR2A | P28223 | Serotonin 5-HT2A receptor |
| CHRM1 | P11229 | Muscarinic M1 receptor |
| ADRA2A | P08913 | Alpha-2A adrenergic receptor |
| ADRB2 | P07550 | Beta-2 adrenergic receptor |
| HRH1 | P35367 | Histamine H1 receptor |
| GABRA1 | P14867 | GABA-A alpha-1 |
| SERT | P31645 | Serotonin transporter |
| DAT | Q01959 | Dopamine transporter |

## Data

- Ligand–receptor pairs: the 41,271 pairs (56,637 records) frozen in Paper 1's
  `data/real/` artefacts. No new bioactivity records are added.
- Structures: reference PDB entries (holo preferred) per receptor; AFDB predicted
  structures as the comparison arm. Pocket = residues within 6.5 A of the
  co-crystallized ligand, cross-checked against UniProt binding-site annotations.

## Hypotheses (fixed before data work)

- **H1 (geometry):** a 3D-grounded model (Arm C/D) achieves higher scaffold-disjoint
  Pearson r than Paper 1's cross-attention conditioning (Arm B) on data-rich receptors.
- **H2 (control):** Arm C/D significantly outperforms the wrong-pocket-3D control
  (Arm E) — i.e., the gain, if any, comes from true pocket geometry.
- **H3 (identity vs geometry):** Arm C/D outperforms the shuffled-coordinate control
  (Arm F) — geometry, not residue identity alone, carries the signal.
- **H4 (practicality):** AFDB-predicted structures give the same qualitative conclusion
  as crystal structures.

## Primary endpoint

Paired difference in scaffold-disjoint Pearson r (5 seeds) between Arm C and Arm E,
pooled across the ten data-rich receptors, tested with a two-sided paired Wilcoxon
signed-rank test across seeds; 95% bootstrap CI (1,000 resamples); Holm correction
across the 11 receptors for per-receptor claims. Alpha = 0.05.

Secondary endpoints: temporal-split r (identical protocol to Paper 1), low-resource
behaviour (GABRA1, ADRA2A under the minimum-data guard), and the radius sweep
(5.0/6.5/8.0 A).

## Decision rules (fixed now)

1. If H2 is not supported (3D arm fails to beat wrong-pocket-3D): the paper reports a
   decisive negative result — 1D embeddings, 3D geometry, and shuffled controls are
   statistically indistinguishable on measured data. This is a finding, not a failure.
2. If H2 is supported but H3 is not: report that residue identity, not geometry,
   drives the gain — still a mechanistic finding.
3. No endpoint, threshold, receptor set, or test may be changed after the first
   structure is downloaded. Any deviation is appended here with a dated note and
   flagged in the manuscript.

## Non-negotiables

- Zero simulation; every number from an executed run with a frozen artefact.
- Arms C, E, F land in the same commit.
- Split definitions and seeds are identical to Paper 1 (frozen in `data/real/`).
