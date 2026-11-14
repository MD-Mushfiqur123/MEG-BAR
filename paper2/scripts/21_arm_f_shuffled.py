#!/usr/bin/env python3
"""Phase 21 - Arm F (shuffled-coordinates control): identical architecture
and training budget as Arm C, but the pocket geometry (graph adjacency and
distances) is permuted against residue identity with a fixed per-receptor
permutation. Separates "geometry" from "residue identity" (H3).

Run:  python3 paper2/scripts/21_arm_f_shuffled.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import STORE_PATH, run_arms  # noqa: E402


def main():
    run_arms(['pocket3d_shuffled'])
    print('[OK] Phase 21 complete -> %s' % STORE_PATH)
    return 0


if __name__ == '__main__':
    sys.exit(main())
