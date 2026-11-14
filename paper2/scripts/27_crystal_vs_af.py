#!/usr/bin/env python3
"""Phase 27 - crystal-vs-AF comparison (H4).

Rebuilds every receptor's pocket graph from the AlphaFold DB v6 predicted
model at the SAME UniProt pocket positions as the crystal pocket (so node
identity, ESM-2 features, and pLDDT are unchanged; only the coordinate
source differs), then runs the hypothesis arm (pocket3d) and its
wrong-pocket control on Paper 1's exact scaffold-disjoint splits.

Question: does predicted-structure grounding behave like crystal grounding?
Run:  python3 paper2/scripts/27_crystal_vs_af.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from stage3_common import (REPO as _REPO, load_data, receptor_splits,  # noqa: E402
                           run_arms)
import stage5_common  # noqa: E402

OUT_DIR = os.path.join(_REPO, 'paper2', 'results', 'stage5')
AF_STORE = os.path.join(OUT_DIR, 'af_results.json')
CRYSTAL_STORE = os.path.join(_REPO, 'paper2', 'results', 'stage3',
                             'arms_scaffold_results.json')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df, FP, y, SCAFF, genes = load_data()
    splits = receptor_splits(df, SCAFF, genes)
    af_ctx, af_meta = stage5_common.build_af_context(genes)
    run_arms(
        ['pocket3d', 'pocket3d_wrongpocket'],
        protocol='E3', splits=splits, store_path=AF_STORE, ctx=af_ctx,
        purpose=('Paper 2 Stage 5 Phase 27: pocket3d + wrong-pocket control '
                 'with AFDB v6 predicted-structure geometry at the crystal '
                 'pocket UniProt positions (H4 crystal-vs-AF)'),
        proto_desc=('E3 scaffold-disjoint splits; pocket geometry from '
                    'AFDB v6 models instead of crystal structures'))

    with open(AF_STORE) as fh:
        af = json.load(fh)
    with open(CRYSTAL_STORE) as fh:
        cr = json.load(fh)
    comp = {}
    for g in genes:
        k = 'E3|%s' % g
        if k not in af or 'seeds' not in af[k].get('pocket3d', {}):
            continue
        row = {}
        for arm in ('pocket3d', 'pocket3d_wrongpocket'):
            row[arm] = {'af_mean_r': af[k][arm]['mean_r'],
                        'crystal_mean_r': cr[k][arm]['mean_r'],
                        'delta_r': round(af[k][arm]['mean_r']
                                         - cr[k][arm]['mean_r'], 5)}
        comp[g] = row
    summary = {
        'purpose': 'Phase 27 crystal-vs-AF geometry comparison (H4)',
        'afdb_context_meta': af_meta,
        'per_receptor': comp,
        'pooled_delta_r_pocket3d': round(float(np.mean(
            [v['pocket3d']['delta_r'] for v in comp.values()])), 5) if comp else None,
    }
    with open(os.path.join(OUT_DIR, 'af_comparison.json'), 'w') as fh:
        json.dump(summary, fh, indent=1)
    for g, row in comp.items():
        print('  %-8s AF %.4f vs crystal %.4f (delta %+.4f)'
              % (g, row['pocket3d']['af_mean_r'],
                 row['pocket3d']['crystal_mean_r'],
                 row['pocket3d']['delta_r']), flush=True)
    print('[OK] Phase 27 complete -> %s' % os.path.relpath(AF_STORE, _REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
