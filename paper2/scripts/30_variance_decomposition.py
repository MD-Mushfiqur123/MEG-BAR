#!/usr/bin/env python3
"""Phase 30 - seed and split variance decomposition.

Measured decomposition of Pearson-r variance across the frozen stores:
  - E3 scaffold-disjoint store (all arms): variance across seeds,
    receptors, and arms.
  - E5 temporal store vs E3: split-protocol variance per (receptor, arm).
No model fitting - variance accounting on measured numbers only.

Run:  python3 paper2/scripts/30_variance_decomposition.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from stage3_common import REPO as _REPO  # noqa: E402

OUT_DIR = os.path.join(_REPO, 'paper2', 'results', 'stage5')
E3_STORE = os.path.join(_REPO, 'paper2', 'results', 'stage3',
                        'arms_scaffold_results.json')
E5_STORE = os.path.join(_REPO, 'paper2', 'results', 'stage4',
                        'temporal_results.json')
ARMS = ['shared', 'ridge', 'crossattn_1d', 'pocket3d', 'dist_bias',
        'pocket3d_wrongpocket', 'pocket3d_shuffled']


def seed_grid(store, prefix, arms):
    """List of ((gene, arm), per-seed r values) from a store."""
    out = []
    for key in sorted(k for k in store if k.startswith(prefix + '|')):
        g = key.split('|', 1)[1]
        for arm in arms:
            blk = store[key].get(arm, {})
            if 'seeds' not in blk:
                continue
            out.append(((g, arm), [s['pearson_r'] for s in blk['seeds']]))
    return out


def decomposition(grid):
    """Variance accounting: total = receptor + arm + residual (means-based)."""
    r = np.array([v for _, v in grid], float)
    gs = np.array([k[0] for k, _ in grid])
    ar = np.array([k[1] for k, _ in grid])
    total = float(r.var())
    grand = float(r.mean())
    rec_eff = {g: float(r[gs == g].mean()) for g in sorted(set(gs))}
    arm_eff = {a: float(r[ar == a].mean()) for a in sorted(set(ar))}
    rec_var = float(np.var([rec_eff[g] for g in gs]))
    arm_var = float(np.var([arm_eff[a] for a in ar]))
    return {
        'n_cells': int(r.size), 'grand_mean_r': round(grand, 5),
        'total_var': round(total, 6),
        'receptor_var_share': round(rec_var / total, 4) if total else None,
        'arm_var_share': round(arm_var / total, 4) if total else None,
        'residual_var_share': round((total - rec_var - arm_var) / total, 4)
        if total else None,
        'within_cell_seed_sd_mean': round(float(np.mean(
            [float(np.std(v, ddof=1)) for _, v in grid if len(v) > 1])), 5),
        'arm_means': {a: round(v, 5) for a, v in sorted(arm_eff.items())},
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out = {'phase': 30,
           'purpose': 'seed x receptor x arm variance decomposition + '
                      'split-protocol variance (measured only)'}
    with open(E3_STORE) as fh:
        e3 = json.load(fh)
    grid3 = seed_grid(e3, 'E3', ARMS)
    out['e3_scaffold'] = decomposition(grid3)

    if os.path.exists(E5_STORE):
        with open(E5_STORE) as fh:
            e5 = json.load(fh)
        grid5 = seed_grid(e5, 'E5', ARMS)
        out['e5_temporal'] = decomposition(grid5)
        m3 = {k: float(np.mean(v)) for k, v in grid3}
        m5 = {k: float(np.mean(v)) for k, v in grid5}
        diffs = [m3[k] - m5[k] for k in sorted(set(m3) & set(m5))]
        out['e3_minus_e5'] = {
            'n_cells': len(diffs),
            'mean_delta_r': round(float(np.mean(diffs)), 5),
            'sd_delta_r': round(float(np.std(diffs, ddof=1)), 5)
            if len(diffs) > 1 else None,
            'min_delta_r': round(float(np.min(diffs)), 5),
            'max_delta_r': round(float(np.max(diffs)), 5),
        }
    out_path = os.path.join(OUT_DIR, 'variance_decomposition.json')
    with open(out_path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print('[OK] Phase 30 complete -> %s' % os.path.relpath(out_path, _REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
