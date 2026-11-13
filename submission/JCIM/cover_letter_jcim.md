# Cover Letter — Submission to the Journal of Chemical Information and Modeling (JCIM)

**Date:** November 13, 2026
**To:** Prof. Kenneth M. Merz, Editor-in-Chief, and the Editors
**Journal:** *Journal of Chemical Information and Modeling* (ACS)
**Manuscript Type:** Article
**Article Title:** Ligand Fingerprints, Not Expert Routing or Pocket Conditioning, Drive Cross-Family Affinity Prediction in Protein Foundation Models: A Controlled Study on 56,637 Measured ChEMBL Records

---

**Corresponding Author:**
**Md Mushfiqur Rahim**
Independent Researcher (Clinical Neuroscience & AI Systems Architecture), Bogura, Bangladesh
- ORCID: [0009-0003-1021-685X](https://orcid.org/0009-0003-1021-685X)
- GitHub: https://github.com/MD-Mushfiqur123/MEG-BAR
- Email: 20mahin2020@gmail.com
- Preprint DOI: [10.6084/m9.figshare.35002837](https://doi.org/10.6084/m9.figshare.35002837) (figshare, CC BY 4.0)

---

Dear Prof. Merz and the Editors of *JCIM*,

I am pleased to submit the above Article for consideration in the *Journal of Chemical Information and Modeling*.

Protein foundation models such as ESM-2 encode transferable structural and evolutionary features, and recent work has proposed sparse expert-routing overlays with router re-anchoring as a route to modular drug–receptor specialization — accompanied by simulated reports of large accuracy margins. This manuscript asks a simple question: **what survives measurement?**

To answer it, I curated 56,637 measured K_i/IC50/K_d records for eleven human receptors from ChEMBL (41,271 unique receptor–ligand pairs), combined 2048-bit Morgan fingerprints with embeddings from the genuine frozen ESM-2 650M checkpoint, and ran a five-seed, scaffold-disjoint and temporal evaluation with three decisive controls. The findings are a controlled negative result:

1. **Router blindness is measured, not cured:** the trained router stays near-uniform (gate entropy ≥ 93% of maximum) and never outperforms a frozen-uniform router.
2. **Pocket structure contributes nothing measurable:** cross-attention receptor conditioning yields small, statistically insignificant gains (paired Wilcoxon p ≥ 0.0625), and a wrong-pocket control — deliberately supplying the wrong pocket residues — reproduces them.
3. **Fingerprint baselines set the bar:** a Ridge regression on Morgan fingerprints alone is competitive throughout (r = 0.39–0.83) and is the only model with signal on the low-resource receptor (r = 0.53 where the deep models collapse to r ≈ 0.01).

I believe this work fits JCIM's scope precisely: it is a rigorous, fully documented evaluation of how protein foundation-model representations and conditioning mechanisms behave on real medicinal-chemistry data, and it delivers an actionable benchmark for the field — fingerprint features plus simple regressions remain the bar that expert-routing architectures must clear. The manuscript is written with an explicit evidentiary register (measured / computed / simulated / withdrawn), including a public defect register for theoretical claims that failed, which I regard as essential scientific hygiene for this area.

**Preprint disclosure:** a preprint of this manuscript is available on figshare (DOI: 10.6084/m9.figshare.35002837, CC BY 4.0). It has not been published elsewhere and is not under consideration by any other journal.

**Data and code availability:** all curated data artefacts (SHA-256-frozen), evaluation scripts, and the complete audit trail are publicly available at https://github.com/MD-Mushfiqur123/MEG-BAR.

I select the **traditional (subscription, no-fee)** publishing route. As an independent researcher without institutional funding, I would be unable to proceed with an open-access fee.

Thank you for your time and consideration.

Sincerely,
**Md Mushfiqur Rahim**
Independent Researcher
Bogura, Bangladesh
