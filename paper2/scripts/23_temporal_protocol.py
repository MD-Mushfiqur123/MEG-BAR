#!/usr/bin/env python3
"""Phase 23 - temporal protocol: train pre-2015, test 2015+ (pre-registered).

All seven arms, five seeds, identical optimisation budget, granular resume.
Split definition (documented in the artefact): train = document_year < 2015,
validation = scaffold-disjoint 15% of the pre-cutoff pool (Paper 1's split
function), test = document_year >= 2015. Receptors with <120 pre-cutoff or
<30 post-cutoff pairs are skipped (GABRA1: 45 pre-2015 pairs).

Run:  python3 paper2/scripts/23_temporal_protocol.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import REPO, run_arms, temporal_splits  # noqa: E402

OUT_PATH = os.path.join(REPO, 'paper2', 'results', 'stage4', 'temporal_results.json')
ARMS = ['shared', 'ridge', 'crossattn_1d', 'pocket3d', 'dist_bias',
        'pocket3d_wrongpocket', 'pocket3d_shuffled']


def main():
    df_fp = None
    from stage3_common import load_data
    df, FP, y, SCAFF, genes = load_data()
    splits = temporal_splits(df, SCAFF, genes)
    run_arms(ARMS, protocol='E5', splits=splits, store_path=OUT_PATH)
    print('[OK] Phase 23 complete -> %s' % OUT_PATH)
    return 0


if __name__ == '__main__':
    sys.exit(main())
