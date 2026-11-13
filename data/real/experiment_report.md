# MEG-BAR — REAL measured experiment

Data: ChEMBL measured pChEMBL values (Ki/IC50/Kd), deduplicated to
unique (receptor, molecule) pairs. Features: Morgan fingerprint
(2048 bits, radius 2) concatenated with a real receptor context vector
(esm2_mean_pool, dim 1280). No synthetic values anywhere.

## E1 — within-receptor split

| Receptor | n_test | Pearson r | 95% CI | Spearman | RMSE |
|---|---|---|---|---|---|
| CHRM1 | 411 | 0.783 | [0.737, 0.822] | 0.750 | 0.780 |
| DRD2 | 1816 | 0.768 | [0.745, 0.790] | 0.757 | 0.661 |
| GABRA1 | 67 | 0.585 | [0.352, 0.777] | 0.595 | 0.809 |
| HTR2A | 1143 | 0.780 | [0.751, 0.808] | 0.788 | 0.751 |

## E2 — leave-one-receptor-out (zero-shot)

| Held out | Model | Pearson r | 95% CI | Spearman | RMSE |
|---|---|---|---|---|---|
| CHRM1 | shared | 0.204 | [0.160, 0.249] | 0.180 | 1.484 |
| CHRM1 | routed_trained | 0.128 | [0.082, 0.176] | 0.120 | 1.504 |
| CHRM1 | routed_uniform | 0.160 | [0.115, 0.205] | 0.148 | 1.566 |
| DRD2 | shared | 0.227 | [0.206, 0.248] | 0.198 | 1.264 |
| DRD2 | routed_trained | 0.220 | [0.200, 0.241] | 0.190 | 1.286 |
| DRD2 | routed_uniform | 0.217 | [0.197, 0.237] | 0.192 | 1.332 |
| GABRA1 | shared | -0.020 | [-0.145, 0.099] | 0.012 | 2.302 |
| GABRA1 | routed_trained | 0.154 | [0.026, 0.283] | 0.138 | 1.866 |
| GABRA1 | routed_uniform | -0.049 | [-0.167, 0.073] | -0.013 | 2.408 |
| HTR2A | shared | 0.290 | [0.267, 0.316] | 0.282 | 1.359 |
| HTR2A | routed_trained | 0.281 | [0.257, 0.305] | 0.264 | 1.396 |
| HTR2A | routed_uniform | 0.257 | [0.232, 0.283] | 0.246 | 1.427 |

Wall clock: 468.0 s
