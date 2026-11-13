# -*- coding: utf-8 -*-
"""Second audited patch pass: statistical consistency + remaining truth fixes."""
import io
import sys

TEX = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\latex\main.tex'
with io.open(TEX, encoding='utf-8') as fh:
    src = fh.read()

EDITS = []


def add(label, old, new, count=1):
    EDITS.append((label, old, new, count))


# ------------------------------------------------- dataset section: no data used
add(
    'benchmark datasets: no data was retrieved',
    r"""To rigorously evaluate MEG-BAR across diverse receptor chemistries, we assemble an extensive evaluation suite derived from three authoritative public repositories:
\begin{enumerate}[leftmargin=1.5em,noitemsep]
    \item \textbf{BindingDB \citep{gilson2016bindingdb}:} A comprehensive database of measured binding affinities ($K_d, K_i, IC_{50}$). We filter all human neurotransmitter receptor assays, retaining entries with verified quantitative binding constants.
    \item \textbf{ChEMBL 33 \citep{mendez2019chembl}:} High-confidence bioactivity data curated from medicinal chemistry literature. We extract target profiles across the four therapeutic receptor families.
    \item \textbf{PDBbind v2020 Refined Set \citep{wang2004pdbbind,liu2015pdbbind}:} Experimentally resolved 3D crystal complexes with corresponding binding affinities, used for structural cross-validation.
\end{enumerate}""",
    r"""No dataset was downloaded for this manuscript. The three public repositories below define the target corpus for the empirical study this paper specifies, and the corpus sizes that follow are \emph{planned} volumes rather than records that were retrieved:
\begin{enumerate}[leftmargin=1.5em,noitemsep]
    \item \textbf{BindingDB \citep{gilson2016bindingdb}:} A comprehensive database of measured binding affinities ($K_d, K_i, IC_{50}$). The planned protocol filters all human neurotransmitter receptor assays, retaining entries with verified quantitative binding constants.
    \item \textbf{ChEMBL 33 \citep{mendez2019chembl}:} High-confidence bioactivity data curated from medicinal chemistry literature. The planned protocol extracts target profiles across the four therapeutic receptor families.
    \item \textbf{PDBbind v2020 Refined Set \citep{wang2004pdbbind,liu2015pdbbind}:} Experimentally resolved 3D crystal complexes with corresponding binding affinities, intended for structural cross-validation.
\end{enumerate}
\emph{None of these resources contributed a single number to the tables in \cref{sec:results}; every reported value originates instead from the synthetic generator documented in \cref{sec:evidentiary_scope}.}""",
)

# ----------------------------------------------------- Cohen's d recomputed values
add(
    'cohens d DiffDock: recomputed 10.82 with formula',
    r"""Comparing the 1,000 bootstrap correlation iterations reveals a massive effect size of \textbf{Cohen's $d = 11.04$}, indicating complete, unambiguous distribution separation.""",
    r"""Comparing the $1{,}000$ bootstrap correlation iterations with the pooled estimator $d = (\bar{r}_{\text{MEG}} - \bar{r}_{\text{base}})\big/\sqrt{(\sigma_{\text{MEG}}^{2} + \sigma_{\text{base}}^{2})/2}$ yields \textbf{Cohen's $d = 10.82$}, i.e.\ complete separation of the two \emph{simulated} distributions.""",
)

add(
    'cohens d AutoDock: 14.82 -> 15.40',
    r"""and Cohen's $d = 14.82$ across bootstrap correlations.""",
    r"""and Cohen's $d = 15.40$ across bootstrap correlations.""",
)

add(
    'cohens d ESM-2: 16.21 -> 15.80',
    r"""and Cohen's $d = 16.21$.""",
    r"""and Cohen's $d = 15.80$.""",
)

add(
    'conclusion cohens d: 11.04 -> 10.82',
    r"""simulated mean Pearson $r = 0.834$ [95\% CI: $0.813, 0.853$], Cohen's $d = 11.04$,""",
    r"""simulated mean Pearson $r = 0.834$ [95\% CI: $0.813, 0.853$], Cohen's $d = 10.82$,""",
)

# ------------------------------------------- statistical-claim interpretation fix
add(
    'statistical significance interpretation',
    r"""These rigorous statistical tests confirm with overwhelming confidence ($p \ll 10^{-13}$) that MEG-BAR's superiority is genuine, reproducible, and robust across all evaluated neurotransmitter receptor systems.""",
    r"""These tests are internally valid, but their interpretation is bounded: because each model's predictions were synthesised to realise a prescribed correlation, a vanishing $p$-value quantifies how tightly the generator enforces its own design constants. Statistical significance here is a property of the simulation, not evidence that MEG-BAR outperforms any real method.""",
)

# --------------------------------------------------------------- 240 -> real counts
add(
    'agonist/antagonist cohort is simulated, not annotated data',
    r"""across a validation cohort of $240$ pharmacologically annotated GPCR ligands, confirming that MEG-BAR captures dynamic conformational transitions in addition to static binding constants.""",
    r"""across a purely simulated cohort of $240$ GPCR ligands. No ligand record was retrieved, so this figure illustrates an intended capability rather than a demonstrated one.""",
)

add(
    'kinase complex count corrected 240 -> 79',
    r"""We evaluate MEG-BAR against Frozen ESM-2, Full Fine-Tuning, and DiffDock across a curated benchmark of $240$ simulated drug-receptor complexes spanning wild-type and resistant variants of EGFR, BCR-ABL1, BRAF, ESR1, and AR (\cref{tab:oncology_benchmark}).""",
    r"""We evaluate MEG-BAR against Frozen ESM-2, Full Fine-Tuning, and DiffDock across a simulated benchmark of $79$ drug-receptor complexes---$18$ EGFR, $18$ BCR-ABL1, $10$ BRAF, $18$ ESR1, and $15$ AR---stored in \path{data/kinase_resistance_benchmark.json} (\cref{tab:oncology_benchmark}). The file's metadata field advertises $240$ simulated evaluations, but only $79$ complex records exist.""",
)

# ---------------------------------------------------------- +44.0% -> +43.9% exact
add(
    'abstract improvement margin exact',
    r"""$+44.0\%$ over the simulated dense ESM-2 baseline""",
    r"""$+43.9\%$ over the simulated dense ESM-2 baseline""",
)

add(
    'contribution improvement margin exact',
    r"""$+44.0\%$ over the simulated dense ESM-2 condition""",
    r"""$+43.9\%$ over the simulated dense ESM-2 condition""",
)

add(
    'figure 2 caption improvement margin exact',
    r"""($+21.6\%$ and $+44.0\%$)""",
    r"""($+21.6\%$ and $+43.9\%$)""",
)

# ---------------------------------------------------------------- OOD table caveat
add(
    'OOD table honest caveat',
    r"""Predictive performance on target receptor families excluded from initial expert training. Evaluated on unseen chemical scaffolds with Tanimoto dissimilarity $> 0.60$. Simulated benchmark adhering strictly to scientific transparency and open data verification standards.""",
    r"""Predictive performance on target receptor families described as excluded from initial expert training. \emph{Caveat: the $\beta_2$-AR column reproduces the in-distribution Adrenergic entries of the generator output verbatim, so that column is not in fact a held-out receptor; the $MT_1$ column has no counterpart in the generator output at all. Neither column is a valid out-of-distribution measurement (\cref{sec:evidentiary_scope}).}""",
)

# ------------------------------------------------------------------- apply patch
failures = []
for label, old, new, expected in EDITS:
    found = src.count(old)
    if found != expected:
        failures.append('%-56s expected %d, found %d' % (label, expected, found))
        continue
    src = src.replace(old, new)

if failures:
    print('ABORT - no file written. Mismatches:')
    for f in failures:
        print('  ' + f)
    sys.exit(1)

with io.open(TEX, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write(src)
print('OK - %d audited edits applied.' % len(EDITS))
