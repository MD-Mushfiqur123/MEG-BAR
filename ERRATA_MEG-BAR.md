# ERRATA — MEG-BAR Manuscript Corrections

**Source:** `HRJEJy76-06_MEG-BAR_Protein_Foundation_Model_Manuscript_CORRECTED.pdf` (44 pages)
**Corrected version:** `MEG-BAR_Manuscript_CORRECTED_v2.md` (77 targeted replacements, all verified applied)

---

## A. Critical contradictions (Section 9 real experiments vs. "simulation-only" claims)

1. **§5.1, §5.4, §10.1(iv), Acknowledgments, Conclusion, Reproducibility Checklist (items 3 & 4):** Claims that "no experiments were run / results are simulated only" contradicted Section 9's real executed experiments (ChEMBL 33 data, real ESM-2 650M runs). Reworded to acknowledge the real Section 9 experiments while keeping the simulation disclaimer for Sections 1–8.
2. **Abstract / conclusion framing:** "fully reproducible, simulation-based evaluation" claims now scoped to the simulation protocol only.

## B. Theorem / Lemma / Proposition numbering

3. **Lemma 1 → Lemma 2** (unified with the Lipschitz softmax result referenced in the Abstract).
4. **Theorem 3 → Proposition 3; Theorem 4 → Proposition 4** (they are invariance claims, not generalization theorems); all cross-references updated.

## C. Mathematical errors

5. **Algorithm 1 line 12:** summed mask `∇L ⊙ Σ_k M_k` is a no-op (Σ_k M_k = 1). Replaced with a per-domain masked update loop.
6. **Eq. 25:** mask indexed a column `(M_mut)_{ij}` while W_r is N×d; corrected to row-vector form `(M_mut)_{j,:} = 1ᵀ` on target rows; §4 text "non-target expert column…for all i" corrected to row form.
7. **Proposition 4:** plain-GD invariance fails under AdamW weight decay (masked rows decay as (1−ηλ)^t); added decay-excluded-parameter-group caveat.
8. **Proposition 4 matrix orientation:** W_r ∈ ℝ^{d×N} with column partition → ℝ^{N×d} with row partition (consistent with Eq. 25 and Algorithm 1).
9. **§8.3:** removed invalid claim L_lip ≤ 1.0; replaced with the correct Lemma 2 constant ‖u‖₂/τ (‖u‖₂ ≈ √d ≈ 35.8 for LayerNorm outputs, so L_lip ≤ 1.0 does not hold).
10. **Theorem 1 / Eq. 18 / Eq. 39 / Eq. 40:** invalid 1/√N expert-sparsity shrinkage replaced by the correct ln(N/K) factor from covering all C(N,K) active sets: `√(d·r/(N·M_dom))` → `√(K·r·d·ln(N/K)/M_dom)`.
11. **Eq. 66:** same 1/√N → ln(N/K) repair.
12. **Lemma 5:** 2r(d+r) → 2rd (double-counted rank term).
13. **Eq. 60/61:** covering-factor 3× → 5× (corrected entropy-integral constants); **Eq. 63/64:** integral truncation fixed.
14. **Cohen's d formula:** misplaced parenthesis corrected.
15. **Withdrawn claims note (§ intro item 3):** already stated 1/√N, k/N, "103× covering reduction", L_lip ≤ 1.0 withdrawals — now consistent with the repaired body.

## D. Numerical inconsistencies

16. **Abstract + Figure 2 caption + Contributions list:** +43.9% → **+44.0%** over simulated dense ESM-2 (0.834 vs. 0.579 baseline).
17. **Table 9:** 26.8% → **27.4%** (reconciled with §6.6 text).
18. **Mutation adapters:** 32,768 params (0.005%) → **20,480 params (0.003%)**.
19. **Parameter accounting (Abstract, Table 6, Table 15, §6.9, Conclusion):** 0.58M → **0.58M per expert bank (≈6.39M total, 0.98% of the full corridor)**.
20. **Table 14:** "twelve/sixteen" → **fifteen**; mean 0.152 → **0.149**; epinephrine micromolar → **nanomolar**.
21. **§9.6:** "seven of the eight" → **"six of the eight"**.
22. **§7.1 rescue:** ΔpKi +1.28 → **+3.57** (relative to gefitinib on T790M, 5.81).
23. **Appendix E.1:** PDB resolution bound ≤2.8 Å → **≤3.5 Å** (consistent with included structures).

## E. Factual / citation errors

24. **Table 16:** PDB **3SB6 → 3SN6** (β₂AR–Gs complex; resolution 3.20 → 3.50 Å); **6DIJ → 6OIJ** (M1–iperoxo–G11; resolution 3.00 → 3.30 Å, G11 protein added).
25. **Residue numbering (§6.3, Figure 5 context, Appendix C.1):** Pro341^6.50 → **Pro338^6.50**; Phe382^6.51 → **Phe389^6.51** (all occurrences); C.1 aromatic list deduplicated to "Phe389^6.51 and Phe390^6.52".
26. **GABA_A receptor subunit composition (§5.1, §3.3):** α1β2γ2 (P47870) → **α1β3γ2 (P18505)**.
27. **CNS-MPO citation:** [Mendez et al., 2019] (ChEMBL) → **[Wager et al., 2010]**; full Wager et al. 2010 reference entry added to the bibliography.
28. **Baek et al. (RFdiffusion) reference:** "Justyna Justyna" → **Justas Dauparas**.
29. **Table 1:** "EquilBind [Stirk et al., 2022]" → **"EquiBind [Stärk et al., 2022]"**.
30. **§6.10 / Figure 7:** MSE → **Huber loss** (terminology consistency with §9 and Algorithm 1).
31. **Table 15:** η_outer → **η_router**.

## F. Status-register updates (Section F self-correction list)

32. Items 1, 6, 7, 8, 10, 11 marked **repaired** to reflect the fixes above; Lemma 2 entry notes the §8.3 L_lip usage was removed.

---

*All 77 replacements were applied with exact-match assertions (each old string required to occur exactly once) and verified by post-fix grep checks (zero residual occurrences of the erroneous strings).*
