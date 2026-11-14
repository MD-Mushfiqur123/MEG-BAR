#!/usr/bin/env python3
"""Phase 17 - Arm B (1D conditioning): Paper 1's cross-attention over
structure-derived pocket-residue ESM-2 embeddings (PCA 1280->128), identical
architecture and optimisation budget to Paper 1's expanded evaluation.

Run:  python3 paper2/scripts/17_arm_b_1d.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import STORE_PATH, run_arms  # noqa: E402


def main():
    run_arms(['crossattn_1d'])
    print('[OK] Phase 17 complete -> %s' % STORE_PATH)
    return 0


if __name__ == '__main__':
    sys.exit(main())
