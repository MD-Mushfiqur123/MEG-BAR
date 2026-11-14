#!/usr/bin/env python3
"""Phase 16 - Arm A (replication): Paper 1's shared fingerprint MLP + Ridge
baseline on the identical frozen scaffold-disjoint protocol.

Regression guard: Arm A must reproduce Paper 1's expanded-evaluation shared
mean_r per receptor (data/real/expanded_results.json, E3 blocks) within
tolerance - the split and data are identical and deterministic, so deviations
can only come from library/hardware nondeterminism.

Run:  python3 paper2/scripts/16_arm_a_replication.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import DATA_REAL, REPO, STORE_PATH, run_arms  # noqa: E402

TOLERANCE = 0.05


def regression_guard(store):
    ref_path = os.path.join(DATA_REAL, 'expanded_results.json')
    if not os.path.exists(ref_path):
        store.data['regression_guard'] = {'error': 'reference artefact missing'}
        return
    with open(ref_path, encoding='utf-8') as fh:
        ref = json.load(fh)
    rows, worst = [], 0.0
    for key, blk in sorted(store.data.items()):
        if not key.startswith('E3|'):
            continue
        g = key.split('|', 1)[1]
        mine = blk.get('shared', {})
        theirs = (ref.get('E3|%s' % g, {}).get('shared', {}) or {}).get('mean_r')
        if 'mean_r' not in mine or theirs is None:
            continue
        delta = abs(mine['mean_r'] - theirs)
        worst = max(worst, delta)
        rows.append({'receptor': g, 'paper2_shared_mean_r': round(mine['mean_r'], 4),
                     'paper1_shared_mean_r': round(theirs, 4),
                     'abs_delta': round(delta, 4),
                     'pass': bool(delta <= TOLERANCE)})
    ridge_rows = []
    for key, blk in sorted(store.data.items()):
        if not key.startswith('E3|'):
            continue
        g = key.split('|', 1)[1]
        mine = blk.get('ridge', {})
        theirs = (ref.get('E3|%s' % g, {}).get('ridge', {}) or {}).get('pearson_r')
        if 'pearson_r' not in mine or theirs is None:
            continue
        ridge_rows.append({'receptor': g,
                           'paper2_ridge_r': round(mine['pearson_r'], 4),
                           'paper1_ridge_r': round(theirs, 4),
                           'abs_delta': round(abs(mine['pearson_r'] - theirs), 4)})
    verdict = 'PASS' if all(r['pass'] for r in rows) else 'FAIL'
    store.data['regression_guard'] = {
        'reference': 'data/real/expanded_results.json (E3 shared, Paper 1 measured)',
        'tolerance': TOLERANCE, 'worst_abs_delta': round(worst, 4),
        'verdict': verdict, 'per_receptor': rows, 'ridge_baseline': ridge_rows,
    }
    print('[guard] Arm A regression vs Paper 1: %s (worst |delta| = %.3f)'
          % (verdict, worst), flush=True)


def main():
    store = run_arms(['shared', 'ridge'])
    regression_guard(store)
    store.flush()
    print('[OK] Phase 16 complete -> %s' % os.path.relpath(STORE_PATH, REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
