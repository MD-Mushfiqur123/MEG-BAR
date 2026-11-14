#!/usr/bin/env python3
"""Phase 28 - pocket-radius sweep (robustness of the H2 conclusion).

Recomputes pockets at 5.0 A and 8.0 A around the SAME chosen ligand copy in
the SAME crystal structures (one deterministic pocket per receptor/radius;
the anti-fishing rule forbids trying alternatives), then runs the hypothesis
arm and its wrong-pocket control on Paper 1's exact scaffold-disjoint splits.

Run:  python3 paper2/scripts/28_radius_sweep.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from stage3_common import (REPO as _REPO, load_data, receptor_splits,  # noqa: E402
                           run_arms)
import stage5_common  # noqa: E402

OUT_DIR = os.path.join(_REPO, 'paper2', 'results', 'stage5')
RADII = (5.0, 8.0)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df, FP, y, SCAFF, genes = load_data()
    splits = receptor_splits(df, SCAFF, genes)
    merged = {'purpose': 'Phase 28 pocket-radius sweep (5.0 / 8.0 A)',
              'radii': {}}
    for radius in RADII:
        store_path = os.path.join(OUT_DIR, 'radius_sweep_%s.json'
                                  % ('%g' % radius).replace('.', 'p'))
        ctx, sweep_meta = stage5_common.build_sweep_context(genes, radius)
        run_arms(
            ['pocket3d', 'pocket3d_wrongpocket'],
            protocol='R%s' % ('%g' % radius).replace('.', 'p'),
            splits=splits, store_path=store_path, ctx=ctx,
            purpose=('Paper 2 Stage 5 Phase 28: pocket3d + wrong-pocket '
                     'control with pockets recomputed at %g A around the '
                     'chosen ligand copy' % radius),
            proto_desc=('E3 scaffold-disjoint splits; pocket defined at '
                        '%g A heavy-atom distance to the chosen ligand copy'
                        % radius))
        with open(store_path) as fh:
            store = json.load(fh)
        merged['radii']['%g' % radius] = {
            'pocket_meta': sweep_meta,
            'results': {k: v for k, v in store.items()
                        if k.startswith('R%s|' % ('%g' % radius).replace('.', 'p'))},
        }
        print('[OK] radius %g A done' % radius, flush=True)
    with open(os.path.join(OUT_DIR, 'radius_sweep.json'), 'w') as fh:
        json.dump(merged, fh, indent=1)
    print('[OK] Phase 28 complete -> paper2/results/stage5/radius_sweep.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
