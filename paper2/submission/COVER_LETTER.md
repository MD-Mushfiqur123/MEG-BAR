# Cover Letter — Paper 2 journal submission

**Date:** 2026-11-14
**To:** The Editors, Journal of Chemical Information and Modeling (ACS)
**From:** Md Mushfiqur Rahim (ORCID 0009-0003-1021-685X),
Independent Researcher, Bogura, Bangladesh — 20mahin2020@gmail.com

Dear Editors,

I am pleased to submit our manuscript, "Three-Dimensional Pocket Geometry
Does Not Beat Its Controls: A Measured Test of Structural Grounding for
Protein Foundation Model Affinity Prediction on 41,271 ChEMBL Pairs," for
consideration as an Article in the Journal of Chemical Information and
Modeling.

This is the pre-registered sequel to my companion study currently under
review at JCIM (Manuscript ID ci-2026-04206a), which measured that 1D
sequence-embedding receptor conditioning fails a wrong-pocket control. The
natural escape route — explicit 3D pocket geometry from crystal structures
— is tested here with six pre-registered model arms, two evaluation
protocols, and 280 trained models on 41,271 measured ChEMBL affinity pairs
across eleven receptors, in 2.34 hours of CPU-only compute.

The result is a decisive, controlled negative: the 3D-grounded arm does not
significantly outperform the wrong-pocket-3D control on the
scaffold-disjoint protocol (+0.00025, p = 0.221) and is significantly worse
on the temporal protocol (−0.0090, p = 0.041). Two practical positives
emerge: AlphaFold DB predicted structures are interchangeable with crystal
structures as geometry sources (pooled Δr = −0.003), and the null is stable
across pocket radii (5.0–8.0 Å). A variance decomposition shows receptor
identity explains 84.5% of outcome variance versus 2.7% for model arm — a
direct, actionable message for practitioners.

We believe this fits JCIM's scope and its demonstrated interest in honest,
controlled evaluations of machine learning for chemical information: the
study is fully pre-registered, contains zero simulated data, reports a
not-run probe transparently, maintains a public defect register, and
releases every frozen artefact with SHA-256 checksums so that any reader
can check, extend, or overturn the conclusion.

The manuscript is not under consideration elsewhere. The preprint is
archived at https://doi.org/10.6084/m9.figshare.35010655 and cited in the
Data and Software Availability section.

Sincerely,
Md Mushfiqur Rahim
ORCID 0009-0003-1021-685X

---

## Suggested reviewers (fill in verified institutional emails before submitting)

1. (name, institution, email) — expertise: protein language models
2. (name, institution, email) — expertise: structure-based affinity prediction
3. (name, institution, email) — expertise: benchmark design / ML evaluation

## Submission checklist

- [ ] Manuscript PDF (9 pp) → "Manuscript PDF File"
- [ ] LaTeX source ZIP (main.tex + figures) → "Manuscript File"
- [ ] TOC graphic (`toc_graphic.png`, 3.25×1.75 in, 300 DPI) → "Table of Contents Graphic"
- [ ] Cover letter (this file, pasted)
- [ ] Preprint disclosure: Yes → https://doi.org/10.6084/m9.figshare.35010655
- [ ] Publishing route: Traditional (subscription, no fee)
- [ ] Link companion Paper 1 (ci-2026-04206a) in the cover letter as done above
