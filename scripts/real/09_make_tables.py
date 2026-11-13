#!/usr/bin/env python3
"""09_make_tables.py - emit LaTeX tables straight from robust_results.json.

Rationale: every number that reaches the manuscript must be traceable to a
measurement artefact. Hand-copying numbers from a JSON file into a .tex table
is exactly how the fabricated r=0.834 figures entered this manuscript in the
first place. This script has no numeric literals of its own: it reads
data/real/robust_results.json and writes latex/generated/real_tables.tex.
Re-running it after the evaluation completes is the only supported way to
update those tables.

Usage:
    python scripts/real/09_make_tables.py

Output:
    latex/generated/real_tables.tex
"""
import json
import os
import itertools

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC = os.path.join(ROOT, 'data', 'real', 'robust_results.json')
OUTDIR = os.path.join(ROOT, 'latex', 'generated')
OUT = os.path.join(OUTDIR, 'real_tables.tex')

NS = 5                     # seeds per reported configuration
ORDER = ['ridge', 'shared', 'crossattn', 'crossattn_wrongpocket']
LABEL = {
    'ridge': 'Ridge',
    'shared': 'shared',
    'crossattn': 'crossattn',
    'crossattn_wrongpocket': 'crossattn (wrong pocket)',
}
DISPLAY = {
    'CHRM1': r'$M_1$ (CHRM1)',
    'DRD2': r'$D_2$ (DRD2)',
    'GABRA1': r'GABA$_{A}\alpha_1$ (GABRA1)',
    'HTR2A': r'$5$-HT$_{2A}$ (HTR2A)',
}


def load():
    with open(SRC, encoding='utf-8') as fh:
        return json.load(fh)


def cell(rec):
    """Return (mean, sd, text) for one architecture record, or None."""
    if not isinstance(rec, dict) or 'skipped' in rec:
        return None
    if 'seeds' not in rec:
        if 'pearson_r' in rec:                      # ridge: single deterministic fit
            return (rec['pearson_r'], 0.0, '%.3f' % rec['pearson_r'])
        return None
    rs = [s['pearson_r'] for s in rec['seeds']]
    if not rs:                                      # block exists but has no seeds yet
        return None
    m = float(np.mean(rs))
    sd = float(np.std(rs, ddof=1)) if len(rs) > 1 else 0.0
    if len(rs) < NS:
        return (m, sd, '%.3f$^{\\dagger}$' % m)      # dagger = incomplete seed set
    return (m, sd, '%.3f' % m)


def block_rows(store, prefix):
    out = []
    for key in sorted(k for k in store if k.startswith(prefix)):
        blk = store[key]
        name = key.split('|', 1)[1]
        cells, means = [], {}
        for arch in ORDER:
            c = cell(blk.get(arch))
            if c is None:
                cells.append('--')
            else:
                cells.append(c[2])
                means[arch] = c[0]
        # bold the best seed-averaged trained model (ridge excluded: not a neural arm)
        trained = {a: v for a, v in means.items()
                   if a in ('shared', 'crossattn', 'crossattn_wrongpocket')}
        if trained and len({r for r in cells if r != '--'}) > 1:
            best = max(trained, key=trained.get)
            idx = ORDER.index(best)
            if cells[idx] != '--':
                cells[idx] = r'\textbf{%s}' % cells[idx]
        out.append((name, cells, means, blk))
    return out


def unwrap(txt):
    return txt.replace(r'\textbf{', '').replace('}', '', 1) if txt.startswith(r'\textbf{') else txt


def value(txt):
    t = unwrap(txt).replace('$^{\\dagger}$', '')
    return float(t)


def significance(means, n_seeds=NS):
    """Paired Wilcoxon across the SEEDS of two arms, reconstructed from the JSON."""
    def arr(m, a):
        rec = m.get(a)
        if not isinstance(rec, dict) or 'seeds' not in rec:
            return None
        v = np.array([s['pearson_r'] for s in rec['seeds']])
        return v if len(v) == n_seeds else None

    pair = (arr(means, 'crossattn'), arr(means, 'crossattn_wrongpocket'))
    if pair[0] is None or pair[1] is None:
        return None
    a, b = pair
    if np.allclose(a, b):
        return None
    try:
        w = stats.wilcoxon(a, b)
        return float(w.pvalue)
    except Exception:                                    # noqa: BLE001
        return None


def fmt_p(p):
    if p is None:
        return '--'
    if p < 0.001:
        return '$<0.001$'
    return '%.3f' % p


def emit_e_protocol(fh, store, prefix, title, label, caption, pending_text):
    rows = block_rows(store, prefix)
    fh.append('%% --------------------------------------------------------------- %s' % title)
    fh.append(r'\begin{table}[!ht]')
    fh.append(r'\centering')
    fh.append(r'\footnotesize')
    fh.append(r'\caption{%s}' % caption)
    fh.append(r'\label{%s}' % label)
    fh.append(r'\resizebox{\linewidth}{!}{%%')
    fh.append(r'\begin{tabular}{l c c c c}')
    fh.append(r'\toprule')
    fh.append(r'\textbf{Split} & \textbf{Ridge} & \textbf{shared} & \textbf{crossattn} & '
              r'\textbf{crossattn} \textbf{(wrong pocket)} \\')
    fh.append(r'\midrule')
    for name, cells, means, blk in rows:
        w = blk.get('wilcoxon_crossattn_vs_shared')
        suffix = ''
        fh.append('%s & %s \\\\' % (DISPLAY.get(name, name), ' & '.join(cells)))
        del suffix
    fh.append(r'\bottomrule')
    fh.append(r'\end{tabular}%')
    fh.append(r'}')
    fh.append(r'\end{table}')
    fh.append('')

    # paired tests, one small table per protocol
    fh.append(r'\begin{table}[!ht]')
    fh.append(r'\centering')
    fh.append(r'\footnotesize')
    fh.append(r'\caption{Paired tests across the %d seeds for %s. '
              r'$\Delta$ is the mean per-seed difference in Pearson $r$. '
              r'At $n=%d$ the two-sided Wilcoxon test cannot return $p<2/2^{%d}=%.4f$, '
              r'so a $p$ at that floor means \emph{all five seeds agreed on the sign}, '
              r'not that the effect is large.}'
              % (NS, title, NS, NS, 2.0 / 2 ** NS))
    fh.append(r'\label{%s-tests}' % label)
    fh.append(r'\begin{tabular}{l c c c c}')
    fh.append(r'\toprule')
    fh.append(r'\textbf{Split} & \textbf{shared} $\rightarrow$ \textbf{crossattn} & '
              r'\textbf{crossattn} $\rightarrow$ \textbf{wrong pocket} & '
              r'$n_{\text{seeds}}$ & \textbf{wrong-pocket wins} \\')
    fh.append(r'\midrule')
    for name, cells, means, blk in rows:
        a = means.get('shared')
        b = means.get('crossattn')
        c = means.get('crossattn_wrongpocket')
        d1 = ('%+.3f' % (b - a)) if (a is not None and b is not None) else '--'
        d2 = ('%+.3f' % (c - b)) if (b is not None and c is not None) else '--'
        wins = ''
        rec_c = blk.get('crossattn')
        rec_w = blk.get('crossattn_wrongpocket')
        if isinstance(rec_c, dict) and isinstance(rec_w, dict) and 'seeds' in rec_c and 'seeds' in rec_w:
            cv = [s['pearson_r'] for s in rec_c['seeds']]
            mv = [s['pearson_r'] for s in rec_w['seeds']]
            if len(cv) == len(mv):
                k = sum(1 for x, y in zip(cv, mv) if y > x)
                wins = '%d/%d' % (k, len(cv))
        fh.append(r'%s & %s & %s & %d & %s \\' % (DISPLAY.get(name, name), d1, d2, NS, wins or '--'))
    fh.append(r'\bottomrule')
    fh.append(r'\end{tabular}')
    fh.append(r'\end{table}')
    fh.append('')

    # human-readable paired p-values (extra scipy call, kept out of the table
    # because a p-value computed from a mean is meaningless - it must be paired)
    fh.append('%% paired Wilcoxon p-values, crossattn vs crossattn_wrongpocket')
    for name, cells, means, blk in rows:
        rc, rw = blk.get('crossattn'), blk.get('crossattn_wrongpocket')
        if not (isinstance(rc, dict) and isinstance(rw, dict)):
            continue
        if 'seeds' not in rc or 'seeds' not in rw:
            continue
        cv = np.array([s['pearson_r'] for s in rc['seeds']])
        mv = np.array([s['pearson_r'] for s in rw['seeds']])
        if len(cv) != len(mv) or len(cv) < 5 or np.allclose(cv, mv):
            continue
        try:
            p = stats.wilcoxon(cv, mv).pvalue
            fh.append('%%   %-8s  p=%.6f  (d=%+.4f)' % (name, p, float((mv - cv).mean())))
        except Exception as exc:                       # noqa: BLE001
            fh.append('%%   %-8s  failed: %s' % (name, exc))
    fh.append('')
    if pending_text:
        fh.append('%% ' + pending_text)


def main():
    store = load()
    os.makedirs(OUTDIR, exist_ok=True)
    L = []
    L.append('%% AUTO-GENERATED by scripts/real/09_make_tables.py')
    L.append('%% Source artefact: data/real/robust_results.json')
    L.append('%% Do not edit by hand. Re-run the generator instead.')
    L.append('')
    emit_e_protocol(
        L, store, 'E3|',
        'E3', 'tab:robust_e3',
        r'\textbf{Phase-1 robust measured results, E3 (scaffold-disjoint within-receptor).} '
        r'Mean Pearson $r$ over five seeds (0--4), Bemis--Murcko scaffold-disjoint split. '
        r'Bold marks the best trained neural arm in each row. '
        r'Ridge is the classical fingerprint baseline. '
        r'$\dagger$ marks a seed set that is still incomplete in the source artefact; '
        r'an incomplete arm is never reported as converged.',
        None)
    emit_e_protocol(
        L, store, 'E4|',
        'E4', 'tab:robust_e4',
        r'\textbf{Phase-1 robust measured results, E4 (leave-one-receptor-out zero-shot transfer).} '
        r'The held-out receptor contributes no training molecule. '
        r'Mean Pearson $r$ over five seeds. ',
        None)

    text = '\n'.join(L) + '\n'
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('[ok] wrote %s (%d chars, %d lines)' % (OUT, len(text), len(L)))

    # console summary, so a human can eyeball what the tables will assert
    for prefix in ('E3|', 'E4|'):
        rows = block_rows(store, prefix)
        print('\n%s  (rows found: %d)' % (prefix, len(rows)))
        for name, cells, means, blk in rows:
            print('  %-8s %s' % (name, '  '.join('%-22s' % c for c in cells)))


if __name__ == '__main__':
    main()
