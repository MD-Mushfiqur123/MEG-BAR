#!/usr/bin/env python3
"""Phase 20 - Arm E (wrong-pocket-3D control, non-negotiable 2): identical
architecture, graph encoder, and training budget as Arm C, but every receptor
is given the NEXT receptor's pocket graph and residue features (sorted order,
Paper 1's wrong-pocket rule). Must land in the same commit as Arm C.

Run:  python3 paper2/scripts/20_arm_e_wrongpocket.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage3_common import STORE_PATH, run_arms  # noqa: E402


def main():
    run_arms(['pocket3d_wrongpocket'])
    print('[OK] Phase 20 complete -> %s' % STORE_PATH)
    return 0


if __name__ == '__main__':
    sys.exit(main())
