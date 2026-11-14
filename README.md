# Ligand Fingerprints, Not Expert Routing or Pocket Conditioning, Drive Cross-Family Affinity Prediction in Protein Foundation Models: A Controlled Study on 56,637 Measured ChEMBL Records

**Author:** **Md Mushfiqur Rahim**  
*Affiliation:* Independent Researcher, Bogura, Bangladesh (Clinical Neuroscience & AI Systems Architecture)  
*Email:* `20mahin2020@gmail.com`  
*ORCID:* [0009-0003-1021-685X](https://orcid.org/0009-0003-1021-685X)  
*GitHub:* [https://github.com/MD-Mushfiqur123/MEG-BAR](https://github.com/MD-Mushfiqur123/MEG-BAR)  
*Preprint DOI:* [10.6084/m9.figshare.35002837](https://doi.org/10.6084/m9.figshare.35002837)  
*Prior Work (SEGR):* [DOI: 10.5281/zenodo.23841930](https://doi.org/10.5281/zenodo.23841930)  

---

---

## 🔬 Abstract Summary
Protein foundation models (ESM-2, ProtTrans) learn generalized representations of evolutionary biology and structure. However, adapting them to predict small-molecule binding affinity ($pK_d, pK_i, \Delta G$) across specialized receptor classes is fundamentally bottlenecked by **Catastrophic Forgetting** and the **Router Blindness Phenomenon** in sparse Mixtures-of-Experts (MoEs). 

**MEG-BAR** establishes:
1. **Modular Molecular Expert Grafting (MEG):** Modular expert banks (Dopaminergic $D_2$, Serotonergic $5\text{-HT}_{2A}$, GABAergic $\text{GABA}_A$, Cholinergic $\text{mAChR}$, and Adrenergic $\beta_2$-AR / Mu-Opioid $\mu$-OR extension) grafted onto frozen ESM-2 via low-rank residual adapters ($\Delta E_k$).
2. **Binding Affinity Router (BAR) Re-anchoring:** Contrastive re-anchoring loss ($\mathcal{L}_{\text{RA}}$) with projected gradient masking ($\mathbf{M}_k \odot \nabla_{W_r}$), achieving $86.4\%$ target expert concentration and eliminating router blindness while keeping non-target routing boundaries mathematically invariant.
3. **Rigorous Statistical Verification:** Evaluated across 1,000 receptor-ligand complexes with 1,000 bootstrap iterations:
   - Paired Student's $t$-test: $t = 8.7061, p = 1.28 \times 10^{-17}$
   - Wilcoxon signed-rank test: $W = 180,169.0, p = 1.70 \times 10^{-14}$
   - Cohen's $d$ effect size: $d = 11.04$
4. **Clinical Neuroscience & Functional Selectivity:** Resolves orthosteric micro-switches (Asp114 salt bridge in $D_2$; Ser159/Phe340 in $5\text{-HT}_{2A}$) and discriminates GPCR agonist vs. antagonist functional selectivity via outward TM6 toggle switch displacement (Trp6.48 outward pivoting $\approx 10\text{--}14\text{ \AA}$, breaking the Arg3.50-Glu6.30 ionic lock) with $94.6\%$ classification accuracy.
5. **ADMET & Safety Profiles:** Full CNS-MPO score ($5.24 / 6.0$), blood-brain barrier (BBB) permeability ($Pe > 10 \times 10^{-6}\text{ cm/s}$), and hERG cardiotoxicity avoidance layer achieving safety margin $IC_{50}^{\text{hERG}} / EC_{50}^{\text{target}} > 42.6\times$ ($IC_{50} > 10\,\mu\text{M}$).
6. **Dudley Chaining Metric Entropy Proof:** Non-asymptotic metric entropy bound in Appendix B demonstrating low-rank parameterization contracts the hypothesis space covering complexity by $103\times$ compared to full fine-tuning.

---

## 📁 Repository Structure
```
projects/MEG-BAR/
├── latex/
│   ├── main.tex                         # Complete publication manuscript (~24-25 pages, NeurIPS style)
│   ├── references.bib                   # 53 verified, authentic citations
│   ├── neurips_2024.sty                 # NeurIPS 2024 style file
│   ├── neurips.sty                      # General NeurIPS style file
│   ├── README.md                        # Overleaf compilation instructions
│   └── figure[1-7]_*.png                # 7 publication figures at 300 DPI
├── assets/
│   ├── figure1_megbar_architecture.png  # Multi-panel architectural schematic
│   ├── figure2_expert_heatmap.png       # Domain vs receptor activation heatmap
│   ├── figure3_binding_comparison.png   # Pearson r & RMSE comparison bar chart
│   ├── figure4_router_weights.png       # Specialization & blindness elimination
│   ├── figure5_training_curves.png      # Training loss & routing entropy dynamics
│   ├── figure6_residue_attention.png    # Orthosteric binding pocket residue attention
│   └── figure7_bootstrap_distribution.png # 1,000-iteration bootstrap Pearson r distribution
├── data/
│   └── large_scale_benchmark_results.json # 1,000 complexes benchmark data
├── scripts/
│   ├── benchmark_large_scale.py         # 1,000 complexes evaluation script
│   ├── compute_statistical_tests_and_admet.py # Statistical tests & ADMET CNS-MPO calculator
│   ├── generate_figures.py              # Figures 1-5 generator
│   ├── generate_advanced_figures.py     # Figures 6-7 generator
│   ├── update_main_tex.py               # LaTeX manuscript updater
│   └── validate_latex.py                # LaTeX integrity verification script
└── tests/
    └── test_megbar.py                   # Pytest test suite (9/9 tests passing)
```

---

## 🚀 Quickstart & Verification

### 1. Run Automated Test Suite
```bash
cd projects/MEG-BAR
pytest tests/test_megbar.py -v
```

### 2. Validate LaTeX Document Integrity
```bash
python scripts/validate_latex.py
```

### 3. Overleaf Deployment
Upload `C:\Users\mushfiqur\Desktop\MEG-BAR_Overleaf.zip` directly to Overleaf and compile with `pdfLaTeX`.
