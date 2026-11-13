# MEG-BAR — REAL Measured Experiment Results

**Executed:** 2026-11-12 · **Agent:** L · **Machine:** AMD Ryzen 5 5600G (6C/12T), 19.9 GB RAM, CPU only
**Verdict in one line:** the pipeline is real and it ran — and the measurements do **not** reproduce the paper's simulated claims.

---

## 1. What was actually run

| Stage | Script | Result |
|---|---|---|
| Retrieve measured bioactivity | `scripts/real/01_fetch_data.py` | **23,872** ChEMBL records (Ki/IC50/Kd) for 4 human receptors |
| Retrieve receptor sequences | same script (UniProt REST) | 443 / 471 / 456 / 460 aa |
| Embed receptors | `scripts/real/02_embed_proteins.py` | real **ESM-2 650M** (651.0M params, 1280-d, 33 layers) → `4 × 1280` |
| Within-receptor + zero-shot | `scripts/real/03_experiment.py` | 468 s wall clock |
| Scaffold-disjoint check | `scripts/real/04_scaffold_eval.py` | 17.9 s, scaffold overlap verified **0** |

**Data reduction:** 23,872 records → median pChEMBL per unique (receptor, molecule) → **17,177 labelled pairs**, **5,693 unique Bemis-Murcko scaffolds**.

| Receptor | ChEMBL target | UniProt | n pairs | median pChEMBL |
|---|---|---|---|---|
| Dopamine D₂ | CHEMBL217 | P14416 | 9,079 | 6.76 |
| Serotonin 5-HT₂A | CHEMBL224 | P28223 | 5,714 | 7.25 |
| Muscarinic M₁ | CHEMBL216 | P11229 | 2,053 | 6.70 |
| GABA-A α₁ | CHEMBL1962 | P14867 | 331 | 7.65 |

*(Note: in the original manuscript's prose, CHEMBL224 was implicitly treated as D₂. It is 5-HT₂A. D₂ is CHEMBL217.)*

**Features:** Morgan fingerprint (2048 bits, radius 2) + real ESM-2 mean-pooled receptor embedding.
**Models:** (i) shared MLP over all receptors; (ii) 4 receptor experts + softmax router, router *trained* vs *frozen uniform* (router-blindness control). Identical budget: Adam lr 1e-3, batch 512, SmoothL1, early stop patience 8, ≤90 epochs.

---

## 2. Within-receptor prediction (`experiment_results.json`, `scaffold_results.json`)

| Receptor | n_train / n_test | Random split r [95% CI] | **Scaffold split r [95% CI]** | ρ (scaffold) | RMSE |
|---|---|---|---|---|---|
| 5-HT₂A | 3885 / 1143 | 0.780 [0.751, 0.808] | **0.664 [0.630, 0.694]** | 0.697 | 0.880 |
| M₁ | 1395 / 411 | 0.783 [0.737, 0.822] | **0.575 [0.498, 0.644]** | 0.580 | 1.050 |
| D₂ | 6173 / 1816 | 0.768 [0.745, 0.790] | 0.559 [0.527, 0.592] | 0.553 | 0.829 |
| GABA-A α₁ | 224 / 67 | 0.585 [0.352, 0.777] | 0.033 [−0.170, 0.222] | −0.068 | 2.195 |

- **Honest generalisable performance is r ≈ 0.56–0.66**, not 0.834.
- A random split **over-states** performance by **0.10–0.21** Pearson r — it is mostly analogue recall.
- GABA-A α₁ is uninformative (n=331); its CI spans zero. Not a negative result, an underpowered one.

## 3. Zero-shot cross-receptor transfer (`experiment_results.json`)

| Held out | Shared r [95% CI] | Routed (trained) r | Routed (uniform) r | Gate entropy / ln4 |
|---|---|---|---|---|
| 5-HT₂A | **0.290 [0.267, 0.316]** | 0.281 [0.257, 0.305] | 0.257 [0.232, 0.283] | 1.343 / 1.386 |
| D₂ | **0.227 [0.206, 0.248]** | 0.220 [0.200, 0.241] | 0.217 [0.197, 0.237] | 1.371 / 1.386 |
| M₁ | **0.204 [0.160, 0.249]** | 0.128 [0.082, 0.176] | 0.160 [0.115, 0.205] | 1.298 / 1.386 |
| GABA-A α₁ | −0.020 [−0.145, 0.099] | **0.154 [0.026, 0.283]** | −0.049 [−0.167, 0.073] | 1.290 / 1.386 |

**Three measured facts:**

1. **Zero-shot transfer is weak:** r ≈ 0.20–0.29 measured, vs 0.812 simulated. Not optimistic — a different regime entirely.
2. **Routing did not help:** the trained router *loses* to the shared model on 3 of 4 held-out receptors. It wins only on GABA-A, the weakest comparison.
3. **The router did not specialise:** gate entropy 1.29–1.37 against max 1.386 = still essentially uniform. Training the router did not escape router blindness on this data. **This is a genuine negative result for the paper's central mechanism.**

---

## 4. Simulation vs measurement, side by side

| Claim | Simulated (original paper) | **Measured** | Status |
|---|---|---|---|
| Within-receptor Pearson r | 0.834 | **0.559 – 0.664** | not reproduced |
| Zero-shot OOD r | 0.812 | **0.20 – 0.29** | not reproduced |
| Router mass on target expert | 85–87% | **near-uniform (H/ln4 ≈ 0.93–0.99)** | not reproduced |
| Specialist > shared | claimed | **shared wins 3/4** | contradicted |
| BBB 96.4%, CNS-MPO 5.24, hERG 42.6× | "measured" | **no such experiment exists** | still unmeasured |
| ESM-2 650M real checkpoint | implied | **yes, 651.0M params run** | genuine |

---

## 5. Why it fell short — mechanism, not excuse

- The ESM-2 receptor embedding is **constant within a receptor**, so it can only act as an identity tag. All predictive burden falls on the fingerprint, and the receptor does not condition the ligand representation. A receptor-conditioned ligand encoder (cross-attention over pocket residues) is the missing ingredient.
- The routing loss is **non-convex** (see Appendix F, item 5), so the gate has no reason to sharpen; measurement confirms it stays at ~1/N.
- Scaffold-disjoint evaluation is the honest default; random splits inflate r by up to 0.21.

## 6. What this means for the paper

The manuscript now contains a real, measured section (§9, 44 pages total). It reports the measurements above and states plainly that the simulated claims do not survive. That is a **publishable negative/benchmark result** — "a specialist-routed protein-foundation architecture does not beat a shared model for cross-receptor affinity prediction on ChEMBL, and scaffold-disjoint evaluation cuts reported r roughly in half." That framing is defensible; the previous one was not.

## 7. Artefacts

```
data/real/raw_activities.csv        23,872 records   (SHA-256 in fetch_manifest.json)
data/real/proteins.json             4 UniProt sequences
data/real/protein_embeddings.npz    4 × 1280 (real ESM-2 650M)
data/real/embed_manifest.json       651.0M params, 33 layers, timings, hashes
data/real/experiment_results.json   E1 + E2, all metrics + bootstrap CIs
data/real/scaffold_results.json     scaffold-disjoint runs, overlap=0 verified
data/real/experiment_report.md      auto-generated tables
data/real/scaffold_report.md        auto-generated tables
latex/real_eval.tex                 the LaTeX section now in the manuscript
```

Every number above comes from an executed run whose output file exists. No simulated value is reported as measured.

— **L**
