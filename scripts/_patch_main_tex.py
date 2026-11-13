# -*- coding: utf-8 -*-
"""Audited patch pass for MEG-BAR main.tex.

Every replacement asserts its expected occurrence count; the script aborts
without writing if any pattern fails, so a partial/corrupt edit is impossible.
"""
import io
import sys

TEX = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\latex\main.tex'

with io.open(TEX, encoding='utf-8') as fh:
    src = fh.read()

EDITS = []


def add(label, old, new, count=1):
    EDITS.append((label, old, new, count))


# ---------------------------------------------------------------- truth fixes
add(
    'contribution-5 honest rewrite',
    r"""    \item \textbf{Empirical State-of-the-Art Validation with Formal Hypothesis Testing:} Across extensive benchmarks on BindingDB, ChEMBL 33, and PDBbind v2020, reinforced by a 1,000-complex bootstrap simulation across 5 receptor families with Wilcoxon signed-rank ($p = 1.70 \times 10^{-14}$) and paired $t$-tests ($p = 1.28 \times 10^{-17}$), MEG-BAR achieves a mean Pearson correlation of $r = 0.834$ [95\% CI: $0.813, 0.853$] ($+21.6\%$ improvement over DiffDock \citep{corso2023diffdock} and $+44.0\%$ over dense ESM-2), while preserving generalist protein evolutionary representations ($+0.04\%$ perplexity drift) and reducing training latency by $77\times$ on a single consumer GPU.""",
    r"""    \item \textbf{A Reproducible, Simulation-Based Evaluation Protocol:} A deterministic, seed-fixed parametric Monte--Carlo harness instantiates a 1,000-complex five-family benchmark with $1,000$-iteration bootstrap confidence intervals and formal hypothesis tests (Wilcoxon signed-rank $p = 1.70 \times 10^{-14}$; paired $t$-test $p = 1.28 \times 10^{-17}$). Under this protocol the generator recovers its own prescribed correlations, yielding a mean Pearson $r = 0.834$ [95\% CI: $0.813, 0.853$] for the MEG-BAR condition ($+21.6\%$ over the simulated DiffDock condition \citep{corso2023diffdock}, $+44.0\%$ over the simulated dense ESM-2 condition). Because those correlations are prescribed rather than learned, they validate the harness and not the model; \cref{sec:evidentiary_scope} enumerates every resulting untested claim.""",
)

add(
    'abstract perplexity drift arithmetic (0.04 -> 0.40)',
    r"""($+0.04\%$ perplexity drift)""",
    r"""($+0.40\%$ perplexity drift)""",
)

add(
    'table row perplexity drift (0.04 -> 0.40)',
    r"""\textbf{MEG-BAR (Ours, Surgically Re-anchored)} & \textbf{7.45} & \textbf{+0.04\% (Virtually Invariant)} & \textbf{0.783} \\""",
    r"""\textbf{MEG-BAR (Ours, Surgically Re-anchored)} & \textbf{7.45} & \textbf{+0.40\% (Virtually Invariant)} & \textbf{0.783} \\""",
)

add(
    'zero-forgetting prose honesty + drift figure',
    r"""The empirical findings in \cref{tab:catastrophic_forgetting} validate our theoretical guarantees: while monolithic fine-tuning degrades language modeling perplexity by $+59.84\%$ (from $7.42$ to $11.86$) and destroys contact map precision (dropping from $0.784$ to $0.612$), MEG-BAR exhibits virtually zero degradation ($+0.04\%$ PPL drift, contact precision $0.783$).""",
    r"""The simulated findings in \cref{tab:catastrophic_forgetting} are consistent with our theoretical guarantees: while monolithic fine-tuning degrades language modeling perplexity by $+59.84\%$ (from $7.42$ to $11.86$) and degrades contact map precision (from $0.784$ to $0.612$), the MEG-BAR condition shows negligible drift ($+0.40\%$ PPL, contact precision $0.783$).""",
)

add(
    'Figure 8 caption delta-r typo (-0.223 -> -0.213)',
    r"""contrasting with severe degradation under monolithic fine-tuning ($\Delta r = -0.223$).""",
    r"""contrasting with severe degradation under monolithic fine-tuning ($\Delta r = -0.213$).""",
)

add(
    'Figure 8 caption simulated qualifier',
    r"""All empirical distributions derived from simulated biophysical benchmark evaluations.""",
    r"""\emph{All distributions are simulation outputs, not measurements (\cref{sec:evidentiary_scope}).}""",
)

# ------------------------------------------------------------ hardware honesty
add(
    'implementation details: no training run',
    r"""Training is executed on a single consumer NVIDIA GPU (or CPU simulation) for $1,000$ steps with batch size $16$.""",
    r"""No training run was executed for this manuscript. The specification above defines the configuration that the simulation harness emulates, and \cref{tab:compute_efficiency} reports the corresponding projected compute profile.""",
)

add(
    'compute table caption: projected not measured',
    r"""Hardware resource consumption, trainable parameter count, training wall-clock time for $1,000$ steps, and relative speedup evaluated on a single NVIDIA GPU.""",
    r"""Trainable parameter count, projected wall-clock time for $1,000$ steps, and relative speedup. \emph{These are analytical projections; no training run was executed on any hardware, so no wall-clock figure in this table is measured (\cref{sec:evidentiary_scope}).}""",
)

add(
    'compute prose: projection not measurement',
    r"""Consequently, training converges in $3.1$ minutes on a single GPU---representing a $77\times$ speedup over monolithic fine-tuning ($238.4$ minutes) and an $85\%$ reduction in peak activation VRAM memory overhead.""",
    r"""Consequently, adaptation is \emph{projected} to converge in $3.1$ minutes, a $77\times$ speedup over the projected monolithic baseline ($238.4$ minutes), with an $85\%$ reduction in peak activation memory. Both the parameter count and the speedup are analytical consequences of training $0.58$M instead of $650$M parameters; neither number has been measured.""",
)

add(
    'reproducibility hardware claim corrected to real machine',
    r"""    \item \textbf{Hardware Specifications:} Experiments were executed on an AMD Ryzen 7 processor with 16 GB RAM and NVIDIA GeForce GPU acceleration running Windows 11 / Linux Ubuntu 22.04 LTS.""",
    r"""    \item \textbf{Hardware Specifications:} No experiment was executed for this manuscript. The simulation harness was run on an AMD Ryzen 5 5600G (6 cores / 12 threads) with 19.9~GB RAM and no CUDA-capable GPU (Radeon integrated graphics; discrete NVIDIA GeForce GT~710 with 2~GB, unsupported by current PyTorch builds). This machine cannot train ESM-2 650M, which is precisely why the evaluation reported here is simulated rather than measured.""",
)

add(
    'reproducibility data availability corrected',
    r"""    \item \textbf{Data Availability:} All benchmark datasets are open-access: BindingDB (\url{https://www.bindingdb.org}), ChEMBL (\url{https://www.ebi.ac.uk/chembl/}), and PDBbind (\url{http://www.pdbbind.org.cn/}).""",
    r"""    \item \textbf{Data Availability:} No bioactivity dataset was downloaded, parsed, or fitted for this manuscript; all affinities are synthetic draws from the generator described in \cref{sec:evidentiary_scope}. The future empirical study is designed against three open-access resources: BindingDB (\url{https://www.bindingdb.org}), ChEMBL (\url{https://www.ebi.ac.uk/chembl/}), and PDBbind (\url{http://www.pdbbind.org.cn/}).""",
)

add(
    'test count corrected to actually verified value',
    r"""    \item \textbf{Automated Test Verification:} All unit tests pass with $100\%$ success rate under \texttt{pytest} (9/9 tests passed in \texttt{tests/test\_megbar.py}).""",
    r"""    \item \textbf{Automated Test Verification:} All $21$ unit tests in \texttt{tests/test\_megbar.py} pass under \texttt{pytest} (re-verified 2026-11-12: \texttt{21 passed in 0.30s}). The suite checks routing axioms, projected-mask invariance, loss composition, and artifact integrity; it validates \emph{software} behaviour, not scientific accuracy.""",
)

# ---------------------------------------------------------------- relabelling
add(
    'results section title',
    r"""\section{Empirical Results \& Analysis}""",
    r"""\section{Simulation Results \& Analysis}""",
)

add(
    'Table 1 lead-in removes BindingDB real-data claim',
    r"""\cref{tab:binding_affinity_results} summarizes the primary benchmark results across the four therapeutic receptor families on the BindingDB test partition.""",
    r"""\cref{tab:binding_affinity_results} summarizes the primary results across the four therapeutic receptor families under the four-family simulation protocol (\cref{sec:evidentiary_scope}); every entry is a generator design target, not a measured score.""",
)

add(
    'Figure 2 caption relabel + percent basis',
    r"""\caption{\textbf{Cross-Family Binding Affinity Prediction Accuracy on BindingDB.} Bar chart comparing Pearson correlation coefficient ($r$) across target receptor classes for ESM-2 Baseline, AutoDock-GPU, DiffDock, and MEG-BAR (Ours). MEG-BAR exceeds the clinical utility threshold ($r \ge 0.80$) across all target families, outperforming DiffDock by $+17.4\%$ and dense ESM-2 by $+50.5\%$.}""",
    r"""\caption{\textbf{Cross-Family Binding Affinity Prediction Accuracy under the Four-Family Simulation Protocol.} Bar chart of Pearson $r$ per target receptor class for the simulated ESM-2, AutoDock-GPU, DiffDock, and MEG-BAR conditions, corresponding to \cref{tab:binding_affinity_results}. In this simulation the MEG-BAR condition exceeds $r = 0.80$ for every family, with margins of $+17.4\%$ over the simulated DiffDock condition and $+50.5\%$ over the simulated dense ESM-2 condition. These margins belong to the four-family table only and differ from the $1{,}000$-complex study of \cref{tab:bootstrap_benchmark} ($+21.6\%$ and $+44.0\%$); both sets describe the simulation's design, not measured quality.}""",
)

add(
    'results prose: simulation instead of proof',
    r"""Furthermore, it surpasses full-parameter fine-tuning ($r = 0.718$), proving that modular sparse expert partitioning provides superior inductive bias compared to monolithic gradient adaptation.""",
    r"""It also sits above the simulated full-parameter fine-tuning condition ($r = 0.718$). That ordering is prescribed by the generator; demonstrating a genuine inductive-bias advantage for modular sparse expert partitioning is the objective of the empirical study outlined in \cref{sec:evidentiary_scope}.""",
)

add(
    'ADMET caption simulated qualifier',
    r"""Physicochemical property distributions and BBB compliance across candidate molecules prioritized by MEG-BAR across the four receptor families. Benchmark evaluated across $1,000$ complexes.""",
    r"""Physicochemical property distributions and BBB compliance across candidate molecules prioritized by the MEG-BAR condition, across four receptor families. \emph{Every value in this table is a fixed reporting constant emitted by the analysis script; no molecular property was computed and no compound was screened (\cref{sec:evidentiary_scope}).}""",
)

add(
    'router caption simulated qualifier',
    r"""\caption{\textbf{Router Allocation Fidelity \& Verification of Elimination of Router Blindness.} (a)~\textbf{MEG-BAR with Contrastive Re-anchoring:} Receptor pocket activations are routed with high specificity ($85.1\%\text{--}87.2\%$) to their corresponding specialist expert. (b)~\textbf{Ablated Baseline (Without Re-anchoring):} The frozen gating router assigns tokens uniformly at random across all experts ($\approx 25\%$), illustrating severe Router Blindness and neutralizing expert specialization.}""",
    r"""\caption{\textbf{Router Allocation Fidelity under the Simulation Protocol.} (a)~\textbf{MEG-BAR condition with contrastive re-anchoring:} the plotted receptor-pocket routing fractions ($85.1\%\text{--}87.2\%$) are a literal array in the figure-generation script. (b)~\textbf{Ablated condition without re-anchoring:} the frozen router assigns tokens uniformly at random across all experts ($\approx 25\%$, severe Router Blindness). The panels illustrate the \emph{intended} behaviour of contrastive re-anchoring; no router was trained or evaluated (\cref{sec:evidentiary_scope}).}""",
)

add(
    'zero-forgetting caption simulated qualifier',
    r"""Evaluation of protein foundation model capabilities before and after domain adaptation. Metrics: Masked language modeling perplexity on UniRef50 ($\text{PPL} \downarrow$), percentage perplexity drift ($\Delta \text{PPL} \downarrow$), and top-$L/5$ long-range contact map prediction precision ($P@L/5 \uparrow$).""",
    r"""Evaluation of protein foundation model capabilities before and after domain adaptation. Metrics: masked language modeling perplexity on UniRef50 ($\text{PPL} \downarrow$), percentage perplexity drift ($\Delta \text{PPL} \downarrow$), and top-$L/5$ long-range contact map prediction precision ($P@L/5 \uparrow$). \emph{All four rows are simulation inputs; no ESM-2 forward pass or perplexity evaluation was run (\cref{sec:evidentiary_scope}).}""",
)

add(
    'oncology table caption simulated qualifier',
    r"""Predictive correlation (Pearson $r$, Spearman $\rho$), error metrics (RMSE, MAE in $pK_i$ units), and router specialization allocation across wild-type and drug-resistant oncological systems.""",
    r"""Predictive correlation (Pearson $r$, Spearman $\rho$), error metrics (RMSE, MAE in $pK_i$ units), and router specialization allocation across wild-type and drug-resistant oncological systems. \emph{Simulation output, not a measured kinase selectivity study (\cref{sec:evidentiary_scope}).}""",
)

add(
    'ablation top-k caption simulated qualifier',
    r"""Evaluation of predictive correlation, inference throughput, and active FLOP ratio across different top-$K$ selection values ($N = 4$ total experts).""",
    r"""Predictive correlation, inference throughput, and active FLOP ratio across top-$K$ selection values ($N = 4$ total experts). \emph{Simulation output (\cref{sec:evidentiary_scope}).}""",
)

add(
    'ablation alpha caption simulated qualifier',
    r"""Impact of contrastive re-anchoring penalty weight on affinity correlation, target routing allocation, and routing entropy.""",
    r"""Impact of the contrastive re-anchoring penalty weight on affinity correlation, target routing allocation, and routing entropy. \emph{Simulation output (\cref{sec:evidentiary_scope}).}""",
)

add(
    'ablation tau caption simulated qualifier',
    r"""Impact of temperature scaling on routing sharpness, gradient Lipschitz bound ($\epsilon/\tau$), target allocation fidelity, and affinity prediction correlation.""",
    r"""Impact of temperature scaling on routing sharpness, the gradient Lipschitz bound ($\epsilon/\tau$), target allocation fidelity, and affinity prediction correlation. \emph{Simulation output (\cref{sec:evidentiary_scope}).}""",
)

add(
    'author contributions wording',
    r"""implemented the computational scripts and empirical benchmarking suites""",
    r"""implemented the computational scripts and simulation benchmarking suites""",
)

add(
    'acknowledgments: data custodians not used',
    r"""The author acknowledges the open-source scientific contributions of the Meta AI Fundamental AI Research (FAIR) team for open-sourcing ESM-2, the AlphaFold team at Google DeepMind, and the curators of BindingDB, ChEMBL, and PDBbind.""",
    r"""The author acknowledges the open-source scientific contributions of the Meta AI Fundamental AI Research (FAIR) team for releasing ESM-2, the AlphaFold team at Google DeepMind, and the maintainers of the Python scientific stack (NumPy, SciPy, Matplotlib) used by the simulation harness. No public bioactivity database was accessed during this work.""",
)

# ------------------------------------------------------------ typographic pass
# 'h' alone is silently promoted to 'ht' by LaTeX and emits a warning; ask for [!ht] explicitly.
add(
    'float specifier h -> !ht',
    r"""\begin{table}[h]""",
    r"""\begin{table}[!ht]""",
    8,
)

# ---------------------------------------------------------------- apply
failures = []
for label, old, new, expected in EDITS:
    found = src.count(old)
    if found != expected:
        failures.append('%-52s expected %d, found %d' % (label, expected, found))
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
