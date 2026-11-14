#!/usr/bin/env python3
"""Phase 24 - low-resource protocol documentation.

The minimum-data guard (MIN_TRAIN=800 for attention arms) is applied
identically in both protocols. This phase formalises the guard behaviour:
which receptors were skipped where, and what the Ridge/shared-only numbers
are for them. No silent substitution is possible by construction.

Run:  python3 paper2/scripts/24_low_resource.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import REPO, STORE_PATH  # noqa: E402

OUT_DIR = os.path.join(REPO, 'paper2', 'results', 'stage4')
TEMPORAL = os.path.join(OUT_DIR, 'temporal_results.json')
ATTENTION = ['crossattn_1d', 'pocket3d', 'dist_bias',
             'pocket3d_wrongpocket', 'pocket3d_shuffled']


def guard_report(store, label):
    rows = {}
    for key, blk in store.items():
        if '|' not in key:
            continue
        g = key.split('|', 1)[1]
        for arch in ATTENTION:
            a = blk.get(arch) or {}
            if 'skipped' in a:
                rows.setdefault(g, {})[arch] = a['skipped']
    return rows


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(STORE_PATH, encoding='utf-8') as fh:
        e3 = json.load(fh)
    e5 = {}
    if os.path.exists(TEMPORAL):
        with open(TEMPORAL, encoding='utf-8') as fh:
            e5 = json.load(fh)
    out = {
        'purpose': 'Phase 24: minimum-data guard behaviour, both protocols',
        'rule': 'attention arms require n_train >= 800 (Paper 1 rule); '
                'shared and Ridge always run; skipped arms are reported as '
                'skipped, never substituted',
        'scaffold_guard_skips': guard_report(e3, 'E3'),
        'temporal_guard_skips': guard_report(e5, 'E5'),
        'ridge_only_receptors': {},
    }
    for g in sorted(set(out['scaffold_guard_skips']) | set(out['temporal_guard_skips'])):
        blk = e3.get('E3|%s' % g, {})
        out['ridge_only_receptors'][g] = {
            'ridge_r': (blk.get('ridge') or {}).get('pearson_r'),
            'shared_mean_r': (blk.get('shared') or {}).get('mean_r'),
        }
    with open(os.path.join(OUT_DIR, 'low_resource.json'), 'w') as fh:
        json.dump(out, fh, indent=2)
    print('[OK] Phase 24 -> paper2/results/stage4/low_resource.json')
    print('  scaffold skips:', {g: len(v) for g, v in out['scaffold_guard_skips'].items()})
    return 0


if __name__ == '__main__':
    sys.exit(main())
