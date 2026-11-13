# MEG-BAR — Final Submission-Ready PDFs

Author: **Md Mushfiqur Rahim** (Independent Researcher — Clinical Neuroscience & AI Systems Architecture)
- Correspondence: 20mahin2020@gmail.com
- ORCID: [0009-0003-1021-685X](https://orcid.org/0009-0003-1021-685X)
- GitHub: [MD-Mushfiqur123](https://github.com/MD-Mushfiqur123)
- Repository: **https://github.com/MD-Mushfiqur123/MEG-BAR**
- This Paper (Preprint DOI): [10.6084/m9.figshare.35002837](https://doi.org/10.6084/m9.figshare.35002837) (figshare, CC BY 4.0)
- Prior Work DOI: [10.5281/zenodo.23841930](https://doi.org/10.5281/zenodo.23841930)

## Files

| File | Pages | Purpose | Submission target |
|---|---|---|---|
| `MEG-BAR_Preprint_Full_47p.pdf` | 47 | Full manuscript: measured evaluation (Sections 3–4) plus the complete simulation-only design study (Appendices A–L), defect register, and proofs | Zenodo DOI, ChemRxiv / bioRxiv preprint |
| `MEG-BAR_JCIM_Journal_30p.pdf` | 30 | Measured-only journal version: design-study appendices removed, all simulated claims in the main body reframed or pointed to the companion preprint | JCIM / Journal of Cheminformatics |

Both PDFs are compiled from the same LaTeX source tree with Tectonic 0.17.0, have no errors and no undefined references, and carry the author identifier footnote (email, ORCID, GitHub, preprint DOI, prior-work DOI) on page 1.

## SHA-256 checksums

```
798cc9afa92ea9513c5ee4ab39f4c326d92e6481d42d0457c36d412f219e1442  MEG-BAR_JCIM_Journal_30p.pdf
6ac6841d68516bacbdc29b7cd6b2040476ce0d570e1956ae14bb391cdc16ea4e  MEG-BAR_Preprint_Full_47p.pdf
```

## Cite as

> Rahim, Md Mushfiqur (2026). *Ligand Fingerprints, Not Expert Routing or Pocket Conditioning, Drive Cross-Family Affinity Prediction in Protein Foundation Models: A Controlled Study on 56,637 Measured ChEMBL Records*. figshare. Preprint. https://doi.org/10.6084/m9.figshare.35002837.v1

## Rebuilding from source

```bash
# preprint (47 pages)
cd latex && tectonic -X compile main.tex

# journal version (30 pages)
cd journal/JCIM && tectonic -X compile main.tex
```

## Title

*Ligand Fingerprints, Not Expert Routing or Pocket Conditioning, Drive Cross-Family Affinity Prediction in Protein Foundation Models: A Controlled Study on 56,637 Measured ChEMBL Records*

Headline measured results: 56,637 ChEMBL records / 41,271 pairs / 11 receptors; scaffold-disjoint five-seed shared-model r = 0.50–0.80; temporal split r = 0.11–0.72; router near-uniform (never beats frozen-uniform); cross-attention gains not significant (p ≥ 0.0625) and reproduced by a wrong-pocket control; Ridge on Morgan fingerprints competitive throughout (r = 0.39–0.83); hERG QSAR ROC-AUC 0.729 [0.706, 0.753]; CNS-MPO(4) 2.62 ± 0.77.
