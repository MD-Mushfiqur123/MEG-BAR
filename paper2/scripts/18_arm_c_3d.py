#!/usr/bin/env python3
"""Phase 18 - Arm C (3D conditioning): pocket-graph encoder (two rounds of
distance-weighted message passing over the true 8 A pocket graph) feeding the
same cross-attention head as Arm B. This is the hypothesis arm.

Run:  python3 paper2/scripts/18_arm_c_3d.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import STORE_PATH, run_arms  # noqa: E402


def main():
    run_arms(['pocket3d'])
    print('[OK] Phase 18 complete -> %s' % STORE_PATH)
    return 0


if __name__ == '__main__':
    sys.exit(main())
