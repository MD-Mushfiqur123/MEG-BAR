#!/usr/bin/env python3
"""Phase 22 - scaffold-disjoint master table.

Assembles the Stage 3 store into the pre-registered master table: all arms x
11 receptors, per-seed Pearson r, mean +/- sd, and 95% bootstrap CIs. No
training happens here - Stage 3's frozen store is the single source.

Run:  python3 paper2/scripts/22_scaffold_master.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import REPO, STORE_PATH  # noqa: E402

OUT_DIR = os.path.join(REPO, 'paper2', 'results', 'stage4')
ARMS = ['ridge', 'shared', 'crossattn_1d', 'pocket3d', 'dist_bias',
        'pocket3d_wrongpocket', 'pocket3d_shuffled']


def seed_ci(rs):
    """95% t-free bootstrap CI over per-seed Pearson r (5 seeds)."""
    a = np.array(rs, float)
    if len(a) < 2:
        return None
    rng = np.random.default_rng(0)
    boots = [a[rng.integers(0, len(a), len(a))].mean() for _ in range(1000)]
    return [round(float(np.percentile(boots, 2.5)), 4),
            round(float(np.percentile(boots, 97.5)), 4)]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(STORE_PATH, encoding='utf-8') as fh:
        store = json.load(fh)
    master = {'purpose': 'Phase 22: scaffold-disjoint master table (from the '
                         'frozen Stage 3 store; no new training)',
              'protocol': store.get('protocol'), 'arms': ARMS, 'receptors': {}}
    for key in sorted(k for k in store if k.startswith('E3|')):
        g = key.split('|', 1)[1]
        blk = store[key]
        rec = {}
        for arch in ARMS:
            a = blk.get(arch) or {}
            if 'skipped' in a:
                rec[arch] = {'skipped': a['skipped']}
            elif arch == 'ridge':
                rec[arch] = {'pearson_r': a['pearson_r'],
                             'bootstrap_ci': a.get('bootstrap_ci')}
            else:
                rs = [s['pearson_r'] for s in a['seeds']]
                rec[arch] = {'mean_r': a['mean_r'], 'sd_r': a['sd_r'],
                             'seed_ci95': seed_ci(rs),
                             'per_seed': {str(s['seed']): round(s['pearson_r'], 4)
                                          for s in a['seeds']},
                             'n_train': a.get('n_train'), 'n_test': a.get('n_test')}
        master['receptors'][g] = rec
    master['regression_guard'] = store.get('regression_guard')
    with open(os.path.join(OUT_DIR, 'scaffold_master.json'), 'w') as fh:
        json.dump(master, fh, indent=2)

    L = ['# Phase 22 - scaffold-disjoint master table', '',
         'Source: frozen Stage 3 store (no new training).', '',
         '| Receptor | ' + ' | '.join(ARMS) + ' |',
         '|---|' + '---|' * len(ARMS)]
    for g, rec in master['receptors'].items():
        row = [g]
        for arch in ARMS:
            a = rec[arch]
            if 'skipped' in a:
                row.append('skipped')
            elif 'mean_r' in a:
                row.append('%.3f\u00b1%.3f' % (a['mean_r'], a['sd_r']))
            else:
                row.append('%.3f' % a['pearson_r'])
        L.append('| ' + ' | '.join(row) + ' |')
    with open(os.path.join(OUT_DIR, 'scaffold_master.md'), 'w') as fh:
        fh.write('\n'.join(L) + '\n')
    print('[OK] Phase 22 -> paper2/results/stage4/scaffold_master.{json,md}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
