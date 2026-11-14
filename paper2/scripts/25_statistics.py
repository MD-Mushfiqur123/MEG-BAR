#!/usr/bin/env python3
"""Phase 25 - pre-registered statistics.

Primary endpoint (PREREGISTRATION.md): paired difference in scaffold-disjoint
Pearson r (5 seeds) between Arm C (pocket3d) and Arm E (wrong-pocket-3D),
pooled across the data-rich receptors, two-sided paired Wilcoxon signed-rank
across seeds; 95% bootstrap CI (1,000 resamples); Holm correction across the
11 receptors for per-receptor claims. Alpha = 0.05.

Also computed (secondary): C vs F, C vs B, B vs A, D vs E, and the same
family on the temporal protocol.

Run:  python3 paper2/scripts/25_statistics.py
"""
import json
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import REPO, STORE_PATH  # noqa: E402

OUT_DIR = os.path.join(REPO, 'paper2', 'results', 'stage4')
TEMPORAL = os.path.join(OUT_DIR, 'temporal_results.json')


def paired(store, a, b, prefix):
    """Paired per-seed differences a-b, pooled across receptors (primary),
    plus per-receptor paired tests (for Holm)."""
    pooled, per_rec = [], {}
    for key in sorted(k for k in store if k.startswith(prefix + '|')):
        g = key.split('|', 1)[1]
        x, y = store[key].get(a, {}), store[key].get(b, {})
        if 'seeds' not in x or 'seeds' not in y:
            continue
        xs = {s['seed']: s['pearson_r'] for s in x['seeds']}
        ys = {s['seed']: s['pearson_r'] for s in y['seeds']}
        d = [xs[s] - ys[s] for s in sorted(xs) if s in ys]
        if d:
            per_rec[g] = d
            pooled += d
    out = {}
    if pooled:
        arr = np.array(pooled)
        res = {'n_pairs': int(len(arr)), 'mean_diff': round(float(arr.mean()), 5),
               'win_loss_tie': [int((arr > 0).sum()), int((arr < 0).sum()),
                                int((arr == 0).sum())]}
        if len(arr) >= 5 and np.any(arr != 0):
            try:
                w = stats.wilcoxon(arr)
                res['wilcoxon_p'] = round(float(w.pvalue), 5)
            except ValueError:
                res['wilcoxon_p'] = 1.0
        rng = np.random.default_rng(0)
        boots = [arr[rng.integers(0, len(arr), len(arr))].mean() for _ in range(1000)]
        res['bootstrap_ci95'] = [round(float(np.percentile(boots, 2.5)), 5),
                                 round(float(np.percentile(boots, 97.5)), 5)]
        out['pooled'] = res
    holm = {}
    for g, d in per_rec.items():
        arr = np.array(d)
        h = {'n_seeds': len(arr), 'mean_diff': round(float(arr.mean()), 5)}
        if len(arr) >= 5 and np.any(arr != 0):
            try:
                h['wilcoxon_p'] = round(float(stats.wilcoxon(arr).pvalue), 5)
            except ValueError:
                h['wilcoxon_p'] = 1.0
        else:
            h['wilcoxon_p'] = None
        holm[g] = h
    # Holm correction across receptors with valid p-values
    valid = [(g, h['wilcoxon_p']) for g, h in holm.items() if h['wilcoxon_p'] is not None]
    m = len(valid)
    order = sorted(valid, key=lambda t: t[1])
    running = 0.0
    for i, (g, p) in enumerate(order):
        adj = min(1.0, (m - i) * p)
        running = max(running, adj)
        holm[g]['holm_p'] = round(running, 5)
        holm[g]['significant_0.05'] = bool(running < 0.05)
    out['per_receptor_holm'] = holm
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(STORE_PATH, encoding='utf-8') as fh:
        e3 = json.load(fh)
    with open(TEMPORAL, encoding='utf-8') as fh:
        e5 = json.load(fh)

    out = {
        'purpose': 'Phase 25: pre-registered statistics (Wilcoxon, bootstrap, Holm)',
        'alpha': 0.05,
        'primary_endpoint': {
            'definition': 'paired Wilcoxon across seeds, Arm C vs Arm E, '
                          'scaffold-disjoint, pooled across data-rich receptors',
            'result': paired(e3, 'pocket3d', 'pocket3d_wrongpocket', 'E3'),
        },
        'secondary': {
            'C_vs_F_shuffled': paired(e3, 'pocket3d', 'pocket3d_shuffled', 'E3'),
            'C_vs_B_1d': paired(e3, 'pocket3d', 'crossattn_1d', 'E3'),
            'B_vs_A_shared': paired(e3, 'crossattn_1d', 'shared', 'E3'),
            'D_vs_E_wrongpocket': paired(e3, 'dist_bias', 'pocket3d_wrongpocket', 'E3'),
        },
        'temporal_protocol': {
            'C_vs_E_wrongpocket': paired(e5, 'pocket3d', 'pocket3d_wrongpocket', 'E5'),
            'C_vs_F_shuffled': paired(e5, 'pocket3d', 'pocket3d_shuffled', 'E5'),
            'C_vs_B_1d': paired(e5, 'pocket3d', 'crossattn_1d', 'E5'),
            'B_vs_A_shared': paired(e5, 'crossattn_1d', 'shared', 'E5'),
        },
    }

    prim = out['primary_endpoint']['result'].get('pooled', {})
    h2_supported = prim.get('wilcoxon_p', 1.0) < 0.05 and prim.get('mean_diff', 0) > 0
    out['h2_verdict'] = ('SUPPORTED' if h2_supported else
                         'NOT SUPPORTED - decisive negative result per '
                         'PREREGISTRATION.md decision rule 1')
    with open(os.path.join(OUT_DIR, 'statistics.json'), 'w') as fh:
        json.dump(out, fh, indent=2)
    p = prim.get('wilcoxon_p')
    print('[H2] C vs E: mean diff %s, Wilcoxon p = %s -> %s'
          % (prim.get('mean_diff'), p, out['h2_verdict']))
    print('[OK] Phase 25 -> paper2/results/stage4/statistics.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
