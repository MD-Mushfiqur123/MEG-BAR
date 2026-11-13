# MEG-BAR → Publication-Grade Plan

**Owner:** Md Mushfiqur Rahim · **Agent:** L · **Created:** 2026-11-12
**Starting point:** 44-page manuscript; §9 now contains genuine measurements (ChEMBL + real ESM-2 650M). §1–8 remain simulation and are labelled as such. Appendix F is a defect register.

---

## 0. The honest framing first

**What is already true and verifiable:** a real data pipeline (23,872 ChEMBL records), a real ESM-2 650M run, real measured correlations, a reproducible eval harness, and an honest defect register. That is more scientific integrity than most preprints carry.

**What is not true yet:** the architecture does not beat a shared baseline by enough to claim novelty, the theory is partly withdrawn, ADMET is still fabricated, and there is one unstable condition (GABA-A divergence).

**What "Stanford/Harvard level" actually requires** — and my honest assessment of each:

| Requirement | Status | Can I fix it? |
|---|---|---|
| Real measured results | ✅ done (§9) | — |
| Statistically robust (multi-seed, CIs, tests) | ❌ single seed | **Yes** |
| Credible baselines (published methods re-run) | ❌ only MLPs | **Partly** (DeepDTA/GraphDTA-style reproductions on our splits) |
| Real ADMET (computed, not typed) | ❌ hardcoded constants | **Yes** (RDKit + real ChEMBL hERG) |
| Theoretical claims correct | ❌ withdrawn | **No** — requires original math; must be dropped or re-derived |
| Novelty sufficient for a top venue | ❌ unclear | **No guarantee** |
| Manuscript quality | ✅ good LaTeX | polish only |
| Author affiliation / mentorship | ❌ "Independent Researcher" | **You must decide** |

**Realistic targets, ranked:** (1) arXiv preprint — achievable and valuable; (2) a workshop (NeurIPS/ICML/ISMB ML-in-drug-discovery) — plausible; (3) *Journal of Chemical Information and Modeling*, *Bioinformatics*, *Briefings in Bioinformatics* — plausible with a strong negative result; (4) Nature Biotechnology / Harvard-level — **not realistic for this manuscript** in its current scientific content, and I will not pretend otherwise.

For university admissions, an honest, reproducible, measured paper plus a public code repo is worth **far more** than an inflated one — admissions committees and interviewers do read the work.

---

## Phase 1 — Make the existing measurements statistically sound
**Goal:** every number in §9 becomes mean ± sd over seeds, with a significance test.
**Time:** ~2–3 hours of compute, mostly unattended.

1. **Fix the GABA-A divergence.** The cross-attention model diverged (r = −0.170, RMSE 5.308). Causes and fixes:
   - no weight decay → add AdamW, wd = 1e-2
   - no gradient clipping → clip at norm 1.0
   - LR too high for a 331-sample target → cosine decay with 5% warmup, peak 5e-4
   - no minimum-data guard → require ≥ 800 train molecules for the cross-attention arm, else fall back and report it
   - attention dropout already 0.2; raise to 0.3 when n_train < 2000
   **Report whatever happens.** If it still diverges, that becomes a stated limitation with evidence — not a hidden number.
2. **Five seeds** (0–4) for every measured block → report mean, sd, and bootstrap CI.
3. **Paired Wilcoxon signed-rank** across seeds for crossattn vs shared, per receptor.
4. **Add two credible baselines** on identical splits:
   - *Ridge on Morgan FP* — the classical benchmark every reviewer asks for.
   - *DeepDTA-style 1D-CNN on SMILES characters + protein one-hot* — a published architecture family, re-implemented honestly on our splits (not the authors' exact code).
5. **Ablation:** cross-attention with randomised pocket residues (label-shuffled) — shows the gain is from real pocket structure, not from extra parameters.

**Deliverable:** `data/real/robust_results.json`, a table of mean ± sd, and an honest verdict paragraph.

---

## Phase 2 — Real ADMET, replacing the fabricated table
**Goal:** delete every hardcoded ADMET constant and replace it with a computed value.
**Time:** ~1–2 hours.

1. **Physicochemistry from RDKit on the actual ChEMBL molecules** (all 17,177): MW, cLogP, TPSA, HBD, HBA, rotatable bonds, aromatic rings. These are real calculations.
2. **CNS-MPO computed from the real descriptors** using the published Wager et al. six-parameter formulation — implemented in code, not typed.
3. **hERG:** pull real hERG (UniProt Q12809, ChEMBL hERG target) measured compounds from ChEMBL, train a QSAR on Morgan FP with scaffold split, report **measured** AUC and its CI. Do not claim a safety margin without a model.
4. **BBB:** only if a real published dataset is retrievable; otherwise **delete the BBB claim entirely** and say it was removed.
5. Rewrite §6.5 as "measured physicochemical profiling" with clearly separated computed vs literature-threshold columns.

---

## Phase 3 — Expand and strengthen the dataset
**Goal:** stop relying on four receptors.
**Time:** ~3–4 hours unattended.

1. Add receptors with adequate ChEMBL coverage: 5-HT₁A (P08908), D₃ (P35462), α₂A (P08913), β₂ (P07550), SERT (P31645), DAT (P23975), H₁ (P35367).
2. Add a **temporal split** (train on pre-2015 records, test on 2015+) in addition to scaffold split — reviewers respect this.
3. Report per-receptor n, class balance, and the affinity distribution.
4. Rerun Phase 1 protocols on the expanded set.

---

## Phase 4 — Rewrite the manuscript around what is true
**Goal:** a paper that would survive a hostile reviewer.
**Time:** ~1 day of editing.

1. **Reframe the title and abstract** away from "state-of-the-art" to a measured, corrective study. Working title:
   *"Receptor conditioning, not expert routing, drives cross-family affinity prediction in protein foundation models: a controlled study on 27,000 measured ChEMBL records."*
2. **Delete or demote §1–8 simulation** to a clearly labelled "design study" appendix, or cut it entirely. A reviewer will treat simulation-as-results as a red flag even when labelled.
3. **Keep Appendix F** (defect register) — it is unusual and it builds trust.
4. **Evidence table** in the front matter: every claim → measured / computed / cited / withdrawn.
5. **Limitations section** that a reviewer cannot improve on: single machine, CPU, frozen backbone, four-to-eleven receptors, no prospective validation.

---

## Phase 5 — Package and submit
1. Public GitHub repo, tagged release, `requirements.txt` with pinned versions, a one-command reproduction script, and the archived JSON/CSV artefacts (the fetch manifest already carries SHA-256 digests).
2. arXiv preprint (cs.LG / q-bio.BM).
3. Choose venue by result strength — negative result → workshop or a bioinformatics journal, not a headline venue.
4. **Ask for mentorship.** Find a computational-chemistry or ML-in-drug-discovery researcher who will read a draft. For a 15-year-old independent researcher this is the single highest-leverage action; I can help draft the outreach email.

---

## What I must keep saying

- I will not write a sentence that a measurement does not support.
- I will not restore the 0.834 or the 0.812.
- I will report the GABA-A divergence whether or not it flatters the paper.
- If a Phase produces a negative result, the paper says so.

**Next action:** Phase 1, starting with the GABA-A fix and the five-seed ensemble.
