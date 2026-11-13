# -*- coding: utf-8 -*-
"""Third audited patch: withdraw invalid theoretical claims, add defect register."""
import io
import sys

TEX = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\latex\main.tex'
with io.open(TEX, encoding='utf-8') as fh:
    src = fh.read()

EDITS = []


def add(label, old, new, count=1):
    EDITS.append((label, old, new, count))


# ------------------------------------------------------- abstract + contributions
add(
    'abstract: drop strictly-convex wording',
    r"""a strictly convex contrastive loss equipped with a projected gradient mask""",
    r"""a contrastive re-anchoring loss equipped with a projected gradient mask""",
)

add(
    'contribution 2: drop convexity + absolute-guarantee language',
    r"""    \item \textbf{Binding Affinity Router (BAR) Re-anchoring with Projected Gradient Masking:} We formulate a strictly convex Contrastive Re-anchoring (CRR) loss based on Kullback-Leibler (KL) divergence, equipped with a projected gradient mask $\mathbf{M}_k \odot \nabla_{W_r}$. This formulation mathematically guarantees that only the target routing centroids are updated toward the receptor binding manifold ($86.4\%$ specialized mass allocation) while non-target routing boundaries remain mathematically invariant, completely eliminating router blindness.""",
    r"""    \item \textbf{Binding Affinity Router (BAR) Re-anchoring with Projected Gradient Masking:} We formulate a Contrastive Re-anchoring (CRR) loss based on Kullback-Leibler (KL) divergence, equipped with a projected gradient mask $\mathbf{M}_k \odot \nabla_{W_r}$ that restricts parameter updates to the target routing centroid. Non-target \emph{logits} are then invariant by construction (\cref{prop:mutation_invariance}); the loss itself is non-convex in $\mathbf{W}_r$, and the projected mask is not a substitute for that missing guarantee (\cref{sec:theory_defects}).""",
)

add(
    'contribution 3: withdraw 1/sqrt(N) and 103x claims',
    r"""    \item \textbf{Theoretical Generalization Bounds and Lipschitz Continuity:} We establish Theorem~\ref{thm:generalization_bound}, formally proving that the generalization error of MEG-BAR is bounded by $\mathcal{O}\left(\frac{\sigma_{\text{spec}}}{\sqrt{M_{\text{dom}}}} + \sqrt{\frac{d \cdot r}{N}}\right)$, strictly tighter than monolithic fine-tuning by a factor proportional to expert sparsity $k/N$. Furthermore, Lemma~\ref{lem:lipschitz} proves Lipschitz continuity of the softmax gating projection under low-rank weight perturbation, and Appendix~\ref{sec:proof_metric_entropy} delivers a complete Dudley chaining metric entropy bound showing a $103\times$ reduction in covering complexity.""",
    r"""    \item \textbf{A Conditional Complexity Sketch and a Lipschitz Bound:} We state a heuristic generalization bound (Theorem~\ref{thm:generalization_bound}), prove that the softmax \emph{probability map} is Lipschitz with constant $\|\mathbf{u}\|_2/\tau$ (Lemma~\ref{lem:lipschitz}), and sketch a Dudley entropy argument. \textbf{These are preliminary results, not established theorems.} In particular the previously claimed $1/\sqrt{N}$ tightening, the $k/N$ expert-sparsity factor, the "$103\times$ covering reduction", and the $L_{\text{lip}} \le 1.0$ constant are all invalid and are withdrawn; \cref{sec:theory_defects} lists each defect with its correction. Excluding the withdrawn items, the theory is best read as a research agenda.""",
)

# ----------------------------------------------------- remarks and body overclaims
add(
    'masked-gradient remark: logits not boundaries',
    r"""This guarantees that the decision boundaries of all non-target experts remain mathematically invariant.""",
    r"""This makes the non-target routing \emph{logits} exactly invariant. It does not make the resulting softmax probabilities or decision boundaries invariant, because the shared softmax denominator still changes when the target centroid moves.""",
)

add(
    'remark: withdraw 1/sqrt(N)',
    r"""Theorem~\ref{thm:generalization_bound} reveals that because the base backbone is frozen and the expert update is constrained to rank $r \ll d$, the complexity term scales with $\sqrt{\frac{d \cdot r}{N}}$ rather than the monolithic full-parameter complexity $\sqrt{d^2 \cdot L}$. The factor $1/\sqrt{N}$ demonstrates that sparse expert partitioning mathematically tightens the generalization bound by confining domain variance to specialized sub-manifolds.""",
    r"""An earlier version of this remark claimed that the complexity term scales with $\sqrt{dr/N}$ and that the factor $1/\sqrt{N}$ therefore tightens the bound. \textbf{That claim is incorrect and is withdrawn.} A uniform-convergence argument over a class containing all $N$ trained adapters must grow with $N$, not shrink with it: replacing $N=1$ by $N=4$ cannot halve a valid bound. What does survive is the weaker and conditional statement that a frozen backbone plus a rank-$r$ update restricts the \emph{updated} parameter count, which is a modelling observation rather than a generalization guarantee.""",
)

add(
    'proposition: withdraw strict convexity',
    r"""Fixing non-target router rows $\{\mathbf{w}_{r, j}\}_{j \neq k}$, the contrastive re-anchoring loss $\mathcal{L}_{\text{RA}}(\mathbf{w}_{r, k})$ with respect to the target centroid $\mathbf{w}_{r, k}$ is strictly convex on any domain where the empirical activation covariance matrix $\mathbf{\Sigma}_k = \frac{1}{|\mathcal{M}_l^{(k)}|} \sum_{\mathbf{u} \in \mathcal{M}_l^{(k)}} \mathbf{u} \mathbf{u}^T \succ 0$ is strictly positive definite. Consequently, gradient descent on $\mathbf{w}_{r, k}$ with learning rate $\eta \le \tau / \|\mathbf{\Sigma}_k\|_2$ converges to a unique global optimum, preventing router entropy collapse to uniform uncertainty ($\mathcal{H} \to \ln N$).""",
    r"""\textbf{Withdrawn.} This statement is false as written and is retained only for provenance. The claim that $\mathcal{L}_{\text{RA}}$ is strictly convex in $\mathbf{w}_{r,k}$ whenever $\mathbf{\Sigma}_k \succ 0$ does not hold: $\mathrm{KL}(p \,\|\, q^{*})$ is convex in the \emph{probability vector} $p$ but $p = \operatorname{softmax}(\mathbf{W}_r\mathbf{u}/\tau)$ is not affine in $\mathbf{W}_r$, so the composition is not convex. For $N=2$, $\tau=1$ and $q^{*}=(0.95, 0.05)$, direct differentiation gives $\partial^{2}\varphi/\partial s^{2} = p(1-p)\left[(1-2p)\ln\!\big(pq_2/((1-p)q_1)\big) + 1\right]$, which is negative at $p = 0.25$---precisely the uniform router-blindness initialisation of \cref{eq:softmax_routing}. The loss is therefore concave exactly where the optimisation starts, and no unique-global-minimiser conclusion follows. A valid repair is to reverse the direction to $\mathrm{KL}(q^{*}\,\|\,p)$, whose negative entropy form \emph{is} jointly convex in the router logits; adopting that repair is left as future work and is not assumed anywhere in this manuscript.""",
)

add(
    'oncology projection overclaim',
    r"""This mathematical projection strictly constrains gradient flow: non-target routing boundaries (including $D_2, 5\text{-HT}_{2A}, \text{GABA}_A, \text{mAChR}$) receive exactly zero gradient ($\nabla_{\mathbf{w}_j} = \mathbf{0}$), theoretically guaranteeing zero perplexity drift and zero accuracy degradation on pre-trained baseline tasks.""",
    r"""This projection strictly constrains gradient flow: the non-target router columns (including $D_2, 5\text{-HT}_{2A}$, $\text{GABA}_A$, $\text{mAChR}$) receive exactly zero gradient ($\nabla_{\mathbf{w}_j} = \mathbf{0}$) under plain gradient descent, so their routing logits are preserved. That is a statement about logits only. It does not imply zero perplexity drift or zero accuracy degradation, because the softmax denominator and the adapter outputs both still change; the numerical values reported later in this section are simulation inputs, not evidence of retention (\cref{sec:evidentiary_scope}).""",
)

add(
    'invariance proof closing line overstated',
    r"""This completes the proof, guaranteeing that routing geometry across all pre-existing neurotransmitter GPCR manifolds ($D_2, 5\text{-HT}_{2A}, \text{GABA}_A, \text{mAChR}$) is mathematically immune to catastrophic drift when oncology adapters are grafted.""",
    r"""This completes the proof, which establishes invariance of the non-target routing \emph{logits} only. It does not establish immunity of the routing distribution, of the expert outputs, or of model accuracy; the phrase ``mathematically immune to catastrophic drift'' that appeared in an earlier draft overstated what is shown and is withdrawn.""",
)

add(
    'convergence proof: remove unique-global-minimiser conclusion',
    r"""By the standard convergence theorem for $L$-smooth, strictly convex functions \citep{boyd2004convex}, gradient descent with step size $\eta \le 1/L_{\text{grad}} \le \tau / \|\mathbf{\Sigma}_k\|_2$ converges to the unique global minimizer $\mathbf{w}_k^*$. At this unique optimum, $p_k(\mathbf{u}) \to q_k^* = 1 - \epsilon_{\text{leak}} = 0.95$, preventing the gating distribution from collapsing to uniform maximum entropy ($\mathcal{H} = \ln N$), which completes the proof.""",
    r"""The appeal to a convergence theorem for $L$-smooth \emph{strictly convex} functions is not available here: as shown in the withdrawal of \cref{prop:convexity}, $\mathcal{L}_{\text{RA}}$ is not convex in $\mathbf{w}_{r,k}$. The Hessian computation above is correct as far as it goes---the block $\mathbf{H}_k = (1/\tau^{2})\,\psi\,\mathbf{u}\mathbf{u}^{\top}$ has the right structure---but the scalar $\psi$ carries a sign-indefinite correction term $(1-2p)(L - \mathrm{KL})$ that dominates near the uniform initialisation, so no global-optimality or uniqueness claim can be made. What can be said is local: on a neighbourhood where $\psi > 0$ and $\mathbf{\Sigma}_k \succ 0$, the objective is locally strictly convex.""",
)

add(
    'dudley intro overclaim',
    r"""This derivation establishes why low-rank molecular expert grafting rigorously prevents overfitting compared to monolithic full-parameter adaptation.""",
    r"""The derivation below is an \emph{incomplete sketch}: it transfers a covering number on the parameter space to a Dudley integral over a function class without establishing the required Lipschitz map, it compares an upper bound for MEG-BAR against a lower bound for monolithic fine-tuning, and it uses inconsistent parameter counts. It therefore does not establish the overfitting claim. The specific defects are itemised in \cref{sec:theory_defects}.""",
)

add(
    '103x conclusion withdrawn',
    r"""This formal mathematical derivation rigorously demonstrates that MEG-BAR contracts the empirical hypothesis space complexity by more than two orders of magnitude ($\approx 103\times$), providing a concrete theoretical explanation for its complete immunity to catastrophic forgetting and superior out-of-distribution sample efficiency.""",
    r"""\textbf{The $103\times$ figure in an earlier draft of this section is withdrawn.} It came from $\sqrt{r/(L d^{2})} = \sqrt{16/(33\cdot 1280^{2})} \approx 1/102.8$, a ratio of \emph{Rademacher-complexity scales} obtained by dividing an upper bound on one side by a lower bound on the other---a comparison with no meaning---and by simultaneously counting a single rank-$16$ matrix on the numerator and the whole $L$-layer model on the denominator. With consistent counting (all $N$ experts, the $13$-layer corridor $[12,24]$, and the three rank-$r$ projections of the adapter), the same ratio is roughly $4$--$7\times$, not $103\times$. No claim of immunity to catastrophic forgetting follows from a complexity bound in any case, because such bounds control target-domain risk rather than retention.""",
)

# --------------------------------------------- evidentiary scope item (i) honesty
add(
    'evidentiary scope: theory is not a clean bill of health',
    r"""are mathematical statements. They hold or fail on their own merits, independently of any experiment, and are the substantive contribution of this work.""",
    r"""are mathematical statements, independent of any experiment. \textbf{They are not, however, all correct.} Several load-bearing results fail as stated---the $1/\sqrt{N}$ tightening, the $k/N$ sparsity factor, the $103\times$ covering reduction, the ``strictly convex'' re-anchoring loss, and the $L_{\text{lip}} \le 1.0$ constant are each invalid---and have been withdrawn in place. \cref{sec:theory_defects} is the defect register. What survives is the softmax Jacobian calculation, the closed-form KL gradient, and exact logit-level invariance under the mask.""",
)

# --------------------------------------------------- appendix: defect register
add(
    'append theoretical defect register',
    r"""\section{Reproducibility Checklist}""",
    r"""\section{Register of Open Defects in the Theoretical Results}
\label{sec:theory_defects}

So that no reader mistakes drafting for proof, we record every known defect in the theoretical development together with its status. Nothing in this register is repaired silently.

\begin{enumerate}[leftmargin=1.5em,itemsep=2pt]
    \item \textbf{Theorem~\ref{thm:generalization_bound}: the $1/\sqrt{N}$ factor is backwards.} The hypothesis class contains all $N$ trained adapters ($Nrd$ parameters), so a uniform-convergence bound must grow with $N$ ($\gtrsim \sqrt{Krd\log(N/K)/M}$), not shrink. Setting $N=1$ or $N=4$ would change a valid bound by a factor of $2$ in the wrong direction. Because the $1/\sqrt{M_{\text{dom}}}$ factor is also dropped in two restatements, the quoted expression does not vanish as $M_{\text{dom}} \to \infty$ and cannot bound a generalization error at all. \emph{Status: withdrawn; needs re-derivation.}
    \item \textbf{Theorem~\ref{thm:generalization_bound}: undefined and misused quantities.} $\sigma_{\text{spec}}$ is a second moment rather than a variance, has unspecified expectation, carries units of loss per parameter while being added to a loss, and is zero at initialisation; $\hat{y}_M$ is a predictor while $\hat{\mathcal E}_{\text{emp}}$ is a risk; $\mathcal{R}_E$ and $\mathcal{R}_W$ appear in the hypotheses but not in the bound; $\delta$ and the union bound over $k$ are missing; the Huber loss is \emph{not} bounded, so the bounded-difference machinery and the $C_{\ell}$ terms do not apply. \emph{Status: open.}
    \item \textbf{``Strictly tighter than monolithic by $k/N$'': asserted, unsupported, self-contradictory.} It is never proved; $k$ is elsewhere an expert index, not a sparsity; and at $K/N = 2/4$ it would imply a $2\times$ gain, contradicting the separately claimed $103\times$ by a factor of about $50$. \emph{Status: withdrawn.}
    \item \textbf{The $103\times$ covering reduction: invalid ratio and inconsistent counting.} An upper bound is divided by a lower bound; the numerator counts one rank-$r$ matrix in one layer while the denominator counts $L d^{2}$ for the entire model; all $N$ experts and the $13$-layer corridor are ignored. Consistent counting gives $\approx 4$--$7\times$. The phrase ``reduction in covering complexity'' also confuses a complexity-scale ratio with a covering-number ratio. \emph{Status: withdrawn.}
    \item \textbf{\cref{prop:convexity}: false as stated.} $\mathrm{KL}(p\|q^{*})$ is convex in $p$ but $p$ is a softmax of $\mathbf{W}_r$, so the composition is non-convex; for the paper's own $q^{*}=(0.95,0.05)$ the second derivative is negative at $p=0.25$, the router-blindness initialisation. The appended convergence and unique-global-minimiser conclusions therefore do not follow. \emph{Status: withdrawn; repair is to use $\mathrm{KL}(q^{*}\|p)$ or to treat the objective as non-convex.}
    \item \textbf{\cref{lem:lipschitz}: correct core, wrong constant and wrong scope.} The Jacobian steps are valid, but the hypothesis $\|\mathbf{u}\|_2 \le 1$ is false for a LayerNorm output ($\|\mathbf{u}\|_2 \approx \sqrt{d} \approx 35.8$), so the true constant is $\|\mathbf{u}\|_2/\tau$, not $1/\tau$, and the claim $L_{\text{lip}} \le 1.0$ is false. The proof never uses low-rank structure, and it bounds the full softmax $p$ rather than the deployed top-$K$-renormalised gate $g$ (argmax selection is discontinuous and has no Lipschitz constant). \emph{Status: restated below; the headline claim is withdrawn.}
    \item \textbf{Algorithm~\ref{alg:megbar_training}: the mask is a no-op.} The update uses $\sum_k \mathbf{M}_k \odot \nabla$, but every row $j$ is masked in exactly one $M_j$, so $\sum_k \mathbf{M}_k = \mathbf{1}$ and the projection does nothing. The intended per-domain mask must be applied in a per-domain loop. \emph{Status: implementation defect, unpatched.}
    \item \textbf{\cref{prop:mutation_invariance}: invariance holds for plain GD only.} The proof assumes $\mathbf{W} \leftarrow \mathbf{W} - \eta\nabla$, but the specified optimiser is AdamW with weight decay $0.01$; masked rows still decay as $\mathbf{w}_j^{(t)} = (1-\eta\lambda)^{t}\mathbf{w}_j^{(0)}$, so strict invariance for all $t \ge 0$ is false for the stated optimiser. \emph{Status: needs restatement either for plain SGD or with a decay-excluded parameter group.}
    \item \textbf{Parameter accounting.} $0.58$M matches a single rank-$16$ adapter pair with the router, not the $13$-layer corridor with the three rank-$r$ projections of the adapter definition, which is closer to $6.39$M ($\approx 0.98\%$ of the backbone). Both counts are reported in \cref{sec:evidentiary_scope}; the smaller figure should not be read as the full adaptor footprint.
    \item \textbf{Notation collisions.} $\mathbf{W}_r \in \mathbb{R}^{N \times d}$ (rows are experts) is used in the method while $\mathbb{R}^{d \times N}$ (columns are experts) is used in the invariance proof; $\mathbf{M}_k$ is declared $\{0,1\}^{N \times d}$ but indexed with three subscripts; sequence length $L$ collides with layer count $L$; \cref{lem:lipschitz} compiles as Lemma~2 because the \texttt{lemma} counter is shared with \texttt{theorem}. \emph{Status: to be unified.}
    \item \textbf{Minor false inequality in the entropy bound.} $(1+4\mathcal{R}_A\mathcal{R}_B/\varepsilon)^{rd} \le (3\mathcal{R}_A\mathcal{R}_B/\varepsilon)^{rd}$ is false ($1+4x > 3x$ for all $x>0$); the correct factor is $5$. The integral is also extended past the support of the covering number instead of being truncated at $\min(D_H, 3\mathcal{R}_A\mathcal{R}_B)$, and the lemma states $2r(d+r)$ while its own proof and the following display use $2rd$.
\end{enumerate}

\section{Reproducibility Checklist}""",
)

# ------------------------------------------------------------------- apply
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
