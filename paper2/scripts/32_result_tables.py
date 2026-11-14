#!/usr/bin/env python3
"""Phase 32 - master result tables.

One CI-annotated master table (all arms x receptors x splits) generated
from the frozen stores: E3 scaffold-disjoint (Stage 3), E5 temporal
(Stage 4), plus the Stage 5 robustness stores (AFDB geometry, radius
sweep). Every number is copied from a measured artefact - no recomputation.

Run:  python3 paper2/scripts/32_result_tables.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from stage3_common import REPO as _REPO  # noqa: E402

OUT_DIR = os.path.join(_REPO, 'paper2', 'results', 'stage6')
ARMS = ['shared', 'ridge', 'crossattn_1d', 'pocket3d', 'dist_bias',
        'pocket3d_wrongpocket', 'pocket3d_shuffled']
ARMS_SHORT = {'shared': 'A', 'ridge': 'A-ridge', 'crossattn_1d': 'B',
              'pocket3d': 'C', 'dist_bias': 'D',
              'pocket3d_wrongpocket': 'E', 'pocket3d_shuffled': 'F'}
STORES = [
    ('E3', 'scaffold-disjoint', os.path.join(_REPO, 'paper2', 'results',
                                             'stage3', 'arms_scaffold_results.json')),
    ('E5', 'temporal', os.path.join(_REPO, 'paper2', 'results',
                                    'stage4', 'temporal_results.json')),
    ('E3AF', 'AFDB geometry', os.path.join(_REPO, 'paper2', 'results',
                                           'stage5', 'af_results.json')),
    ('R5p', 'radius 5.0 A', os.path.join(_REPO, 'paper2', 'results',
                                         'stage5', 'radius_sweep_5p0.json')),
    ('R8p', 'radius 8.0 A', os.path.join(_REPO, 'paper2', 'results',
                                         'stage5', 'radius_sweep_8p0.json')),
]


def fmt_cell(blk):
    if 'skipped' in blk:
        return 'skip'
    if 'seeds' in blk:
        ci = blk.get('bootstrap_ci95')
        base = '%.3f +/- %.3f' % (blk['mean_r'], blk.get('sd_r', float('nan')))
        if ci:
            base += ' [%.3f, %.3f]' % (ci[0], ci[1])
        return base
    if 'pearson_r' in blk:
        base = '%.3f (deterministic)' % blk['pearson_r']
        ci = blk.get('bootstrap_ci')
        if ci:
            base += ' [%.3f, %.3f]' % (ci[0], ci[1])
        return base
    return ''


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    lines = ['# Paper 2 - Master Result Table (Phase 32)', '',
             "Pearson's r, mean +/- sd over 5 seeds, [95% bootstrap CI]. "
             'skip = minimum-data guard (MIN_TRAIN=800).', '']
    for prefix, label, path in STORES:
        if not os.path.exists(path):
            lines += ['## %s (%s): store not yet frozen - omitted' % (prefix, label), '']
            continue
        with open(path) as fh:
            store = json.load(fh)
        genes = sorted(k.split('|', 1)[1] for k in store
                       if '|' in k and isinstance(store[k], dict)
                       and ('pocket3d' in store[k] or 'shared' in store[k]))
        lines += ['## %s - %s' % (prefix, label), '',
                  '| receptor | ' + ' | '.join(ARMS_SHORT[a] for a in ARMS) + ' |',
                  '|---|' + '---|' * len(ARMS)]
        for g in genes:
            key = [k for k in store if k.endswith('|' + g)]
            if not key:
                continue
            blk = store[key[0]]
            cells = [fmt_cell(blk.get(a, {})) for a in ARMS]
            lines.append('| %s | %s |' % (g, ' | '.join(cells)))
        lines.append('')
    out_md = os.path.join(OUT_DIR, 'master_table.md')
    with open(out_md, 'w') as fh:
        fh.write('\n'.join(lines))
    print('[OK] Phase 32 complete -> %s' % os.path.relpath(out_md, _REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
