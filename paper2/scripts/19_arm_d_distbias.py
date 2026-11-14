#!/usr/bin/env python3
"""Phase 19 - Arm D (geometric bias): pocket self-encoder whose attention
logits are biased by the true inter-residue distances (learnable per-head
scale, initialised at zero), feeding the same cross-attention head as Arm B.

Run:  python3 paper2/scripts/19_arm_d_distbias.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import STORE_PATH, run_arms  # noqa: E402


def main():
    run_arms(['dist_bias'])
    print('[OK] Phase 19 complete -> %s' % STORE_PATH)
    return 0


if __name__ == '__main__':
    sys.exit(main())
