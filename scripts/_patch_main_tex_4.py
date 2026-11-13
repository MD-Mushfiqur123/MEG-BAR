# -*- coding: utf-8 -*-
"""Insert the real measured evaluation into main.tex and rescope the honesty box."""
import io
import sys

TEX = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\latex\main.tex'
with io.open(TEX, encoding='utf-8') as fh:
    s = fh.read()

EDITS = []


def add(label, old, new, count=1):
    EDITS.append((label, old, new, count))


add(
    'rescope evidentiary box to exclude the real section',
    r"""This is a \emph{framework, theory, and simulation} study. No protein foundation model was trained, fine-tuned, or evaluated for this work, and no experimental binding assay or public bioactivity record was downloaded or processed. Every quantitative result reported below---in the benchmark, out-of-distribution, zero-forgetting, efficiency, oncology, and ablation sections alike---is the output of a deterministic parametric Monte--Carlo simulation (fixed RNG seed $42$) in which each model's predictions are synthesised by \emph{prescribing} a target correlation against a simulated ground-truth affinity vector.""",
    r"""This is a \emph{framework, theory, and simulation} study with one genuinely executed empirical section. In every section from the benchmark through the ablations, no protein foundation model was trained or fine-tuned and no bioactivity record was used: those results are the output of a deterministic parametric Monte--Carlo simulation (fixed RNG seed $42$) in which each model's predictions are synthesised by \emph{prescribing} a target correlation against a simulated ground-truth affinity vector. \textbf{The exception is \cref{sec:real_eval}, which reports real measurements: $23{,}872$ ChEMBL assay records were retrieved, the genuine ESM-2 650M checkpoint was run, and models were trained and evaluated under scaffold-disjoint splits. Those measurements are real, and they do not reproduce the simulated claims---scaffold-disjoint $r$ is $0.56$--$0.66$ rather than $0.834$, and zero-shot transfer is $r \approx 0.2$--$0.3$ rather than $0.812$.}""",
)

add(
    'insert real evaluation section before Discussion',
    r"""\section{Discussion \& Neuropharmacological Implications}""",
    r"""\input{real_eval}

\section{Discussion \& Neuropharmacological Implications}""",
)

add(
    'abstract points at the measured results',
    r"""\textbf{All numerical results in this manuscript are outputs of a deterministic parametric simulation, not measurements of a trained model; \cref{sec:evidentiary_scope} states precisely what is and is not measured.}""",
    r"""\textbf{Except where noted, all numerical results in this manuscript are outputs of a deterministic parametric simulation, not measurements of a trained model; \cref{sec:evidentiary_scope} states precisely what is and is not measured.} A genuinely executed evaluation is reported in \cref{sec:real_eval}: on $23{,}872$ retrieved ChEMBL assay records with the real ESM-2 650M checkpoint, scaffold-disjoint correlation reaches $r = 0.56$--$0.66$ (not $0.834$) and leave-one-receptor-out transfer only $r \approx 0.20$--$0.29$ (not $0.812$), with a learned router that remains near-uniform.""",
)

failures = []
for label, old, new, expected in EDITS:
    found = s.count(old)
    if found != expected:
        failures.append('%-52s expected %d, found %d' % (label, expected, found))
        continue
    s = s.replace(old, new)

if failures:
    print('ABORT - no file written:')
    for f in failures:
        print('  ' + f)
    sys.exit(1)

with io.open(TEX, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write(s)
print('OK - %d edits applied.' % len(EDITS))
