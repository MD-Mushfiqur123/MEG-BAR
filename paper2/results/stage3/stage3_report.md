# Paper 2 Stage 3 - six model arms, scaffold-disjoint protocol

Protocol: Paper 1's exact Bemis-Murcko scaffold-disjoint within-receptor
split, five seeds (0-4), identical optimisation budget (AdamW wd=0.01,
cosine LR peak 5e-4, batch 512, max 70 epochs, patience 7).

Arms: `shared` (fingerprint MLP), `ridge` (fingerprint Ridge),
`crossattn_1d` (Paper 1 cross-attention on structure-derived pocket
ESM-2, PCA 1280->128), `pocket3d` (pocket-graph encoder -> cross-attention),
`dist_bias` (distance-biased pocket self-attention -> cross-attention),
`pocket3d_wrongpocket` (Arm C on the WRONG receptor's pocket),
`pocket3d_shuffled` (Arm C with geometry permuted against identity).

## Scaffold-disjoint mean Pearson r (5 seeds)

| Receptor | ridge | shared | crossattn_1d | pocket3d | dist_bias | pocket3d_wrongpocket | pocket3d_shuffled |
|---|---|---|---|---|---|---|---|
| ADRA2A | 0.800 | 0.711±0.012 | skipped | skipped | skipped | skipped | skipped |
| ADRB2 | 0.385 | 0.541±0.013 | 0.524±0.013 | 0.521±0.005 | 0.467±0.114 | 0.531±0.017 | 0.519±0.004 |
| CHRM1 | 0.547 | 0.562±0.027 | 0.389±0.217 | 0.534±0.146 | 0.511±0.170 | 0.523±0.168 | 0.453±0.191 |
| DAT | 0.607 | 0.590±0.008 | 0.609±0.012 | 0.604±0.010 | 0.610±0.017 | 0.608±0.014 | 0.603±0.016 |
| DRD2 | 0.521 | 0.577±0.015 | 0.613±0.017 | 0.627±0.012 | 0.607±0.028 | 0.606±0.038 | 0.605±0.011 |
| DRD3 | 0.662 | 0.684±0.004 | 0.717±0.009 | 0.706±0.008 | 0.717±0.006 | 0.713±0.006 | 0.705±0.005 |
| GABRA1 | 0.532 | 0.008±0.005 | skipped | skipped | skipped | skipped | skipped |
| HRH1 | 0.825 | 0.802±0.007 | 0.833±0.005 | 0.837±0.006 | 0.831±0.004 | 0.832±0.012 | 0.837±0.006 |
| HTR1A | 0.601 | 0.682±0.002 | 0.705±0.006 | 0.697±0.008 | 0.705±0.006 | 0.701±0.005 | 0.698±0.002 |
| HTR2A | 0.597 | 0.660±0.010 | 0.688±0.012 | 0.688±0.013 | 0.691±0.007 | 0.695±0.003 | 0.689±0.009 |
| SERT | 0.444 | 0.500±0.003 | 0.520±0.032 | 0.539±0.012 | 0.524±0.041 | 0.542±0.015 | 0.543±0.007 |

## Arm A regression guard vs Paper 1 (shared MLP)

Reference: `data/real/expanded_results.json` E3 shared mean_r.
Tolerance ±0.05. Verdict: **PASS** (worst |delta| 0.000).

| Receptor | Paper 2 shared r | Paper 1 shared r | |delta| | pass |
|---|---|---|---|---|
| ADRA2A | 0.711 | 0.711 | 0.000 | yes |
| ADRB2 | 0.541 | 0.541 | 0.000 | yes |
| CHRM1 | 0.562 | 0.562 | 0.000 | yes |
| DAT | 0.590 | 0.590 | 0.000 | yes |
| DRD2 | 0.577 | 0.577 | 0.000 | yes |
| DRD3 | 0.684 | 0.684 | 0.000 | yes |
| GABRA1 | 0.008 | 0.008 | 0.000 | yes |
| HRH1 | 0.802 | 0.802 | 0.000 | yes |
| HTR1A | 0.682 | 0.682 | 0.000 | yes |
| HTR2A | 0.659 | 0.659 | 0.000 | yes |
| SERT | 0.500 | 0.500 | 0.000 | yes |

Statistical tests (paired Wilcoxon Arm C vs Arm E, bootstrap CIs,
Holm correction) are Phase 25 (Stage 4) and are deliberately not
computed here.

