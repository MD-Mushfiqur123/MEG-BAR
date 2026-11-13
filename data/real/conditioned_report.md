# MEG-BAR — receptor conditioning: measured comparison

Architectures: **shared** (fingerprint only), **const_ctx** (fingerprint +
mean-pooled ESM-2 receptor vector), **crossattn** (ligand tokens cross-attend
to real UniProt-annotated pocket residues, PCA-reduced to 128 dims).
Pocket PCA variance explained: 0.859

## E3 — scaffold-disjoint within-receptor

| Receptor | Arch | Pearson r | 95% CI | Spearman | RMSE |
|---|---|---|---|---|---|
| CHRM1 | shared | 0.587 | [0.515, 0.654] | 0.584 | 1.019 |
| CHRM1 | const_ctx | 0.591 | [0.516, 0.660] | 0.585 | 1.024 |
| CHRM1 | crossattn | 0.592 | [0.520, 0.658] | 0.579 | 1.013 |
| DRD2 | shared | 0.569 | [0.538, 0.601] | 0.570 | 0.849 |
| DRD2 | const_ctx | 0.581 | [0.550, 0.612] | 0.579 | 0.815 |
| DRD2 | crossattn | 0.648 | [0.621, 0.675] | 0.641 | 0.746 |
| GABRA1 | shared | 0.018 | [-0.180, 0.203] | -0.084 | 2.254 |
| GABRA1 | const_ctx | 0.182 | [-0.055, 0.390] | 0.069 | 0.961 |
| GABRA1 | crossattn | 0.002 | [-0.197, 0.189] | -0.104 | 0.898 |
| HTR2A | shared | 0.683 | [0.651, 0.713] | 0.708 | 0.843 |
| HTR2A | const_ctx | 0.676 | [0.644, 0.706] | 0.704 | 0.841 |
| HTR2A | crossattn | 0.693 | [0.661, 0.723] | 0.716 | 0.821 |

## E4 — leave-one-receptor-out

| Held out | Arch | Pearson r | 95% CI | Spearman | RMSE |
|---|---|---|---|---|---|
| CHRM1 | shared | 0.131 | [0.086, 0.177] | 0.122 | 1.591 |
| CHRM1 | const_ctx | 0.096 | [0.053, 0.139] | 0.085 | 1.568 |
| CHRM1 | crossattn | 0.194 | [0.153, 0.233] | 0.151 | 1.612 |
| DRD2 | shared | 0.213 | [0.194, 0.234] | 0.193 | 1.287 |
| DRD2 | const_ctx | 0.210 | [0.190, 0.231] | 0.186 | 1.288 |
| DRD2 | crossattn | 0.215 | [0.195, 0.235] | 0.187 | 1.334 |
| GABRA1 | shared | 0.042 | [-0.086, 0.169] | 0.025 | 2.156 |
| GABRA1 | const_ctx | 0.169 | [0.041, 0.292] | 0.111 | 1.948 |
| GABRA1 | crossattn | -0.170 | [-0.278, -0.059] | -0.152 | 5.308 |
| HTR2A | shared | 0.280 | [0.257, 0.305] | 0.271 | 1.373 |
| HTR2A | const_ctx | 0.283 | [0.259, 0.306] | 0.278 | 1.402 |
| HTR2A | crossattn | 0.288 | [0.265, 0.313] | 0.288 | 1.396 |

Wall clock: 971.3 s
