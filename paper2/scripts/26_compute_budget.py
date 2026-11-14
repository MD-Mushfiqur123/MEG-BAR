#!/usr/bin/env python3
"""Phase 26 - compute budget: honest accounting of what Stage 3/4 cost.

Aggregates per-seed wall-clock seconds from the frozen stores. Everything ran
CPU-only (torch 2.x, 5 threads, no GPU anywhere in the pipeline).

Run:  python3 paper2/scripts/26_compute_budget.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import REPO, STORE_PATH  # noqa: E402

OUT_DIR = os.path.join(REPO, 'paper2', 'results', 'stage4')
TEMPORAL = os.path.join(OUT_DIR, 'temporal_results.json')


def summarise(store):
    per_arm = {}
    for key, blk in store.items():
        if '|' not in key:
            continue
        for arch, a in blk.items():
            if not isinstance(a, dict) or 'seeds' not in a:
                continue
            for s in a['seeds']:
                per_arm.setdefault(arch, []).append(s.get('seconds'))
    return {a: {'n_runs': len([x for x in v if x is not None]),
                'total_s': round(float(np.nansum(v)), 1),
                'mean_s': round(float(np.nanmean(v)), 1)}
            for a, v in sorted(per_arm.items())}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(STORE_PATH, encoding='utf-8') as fh:
        e3 = json.load(fh)
    with open(TEMPORAL, encoding='utf-8') as fh:
        e5 = json.load(fh)
    e3s, e5s = summarise(e3), summarise(e5)
    total = sum(v['total_s'] for v in e3s.values()) + sum(v['total_s'] for v in e5s.values())
    out = {
        'purpose': 'Phase 26: CPU-only compute budget (measured from stores)',
        'hardware': 'CPU-only (no GPU); torch thread count = os.cpu_count()',
        'scaffold_protocol': e3s,
        'temporal_protocol': e5s,
        'total_measured_training_seconds': round(total, 1),
        'total_measured_training_hours': round(total / 3600.0, 2),
        'note': 'excludes feature engineering (Stage 2, minutes) and any '
                'interrupted/retrained runs recorded in DEFECT_REGISTER.md #4',
    }
    with open(os.path.join(OUT_DIR, 'compute_budget.json'), 'w') as fh:
        json.dump(out, fh, indent=2)
    print('[OK] Phase 26 -> paper2/results/stage4/compute_budget.json '
          '(total %.2f h)' % out['total_measured_training_hours'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
