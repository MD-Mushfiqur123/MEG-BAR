"""Phase 12 - Pocket contact maps.

Binary contact maps from the Phase 11 heavy-atom minimum-distance matrix at
4 / 6 / 8 A thresholds, plus a weighted map w = exp(-d / 3 A) truncated at the
8 A shell. Pure numpy.

Output: paper2/data/features/{SYM}_contacts.npz with keys
  contact_4, contact_6, contact_8 [n, n] uint8, weighted [n, n] float32

Run:  python3 paper2/scripts/12_contact_maps.py
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage2_common import FEATURE_DIR, all_symbols, save_json

THRESHOLDS_A = (4.0, 6.0, 8.0)
WEIGHT_SCALE_A = 3.0
WEIGHT_CUTOFF_A = 8.0


def main():
    summary = {"phase": 12, "purpose": "binary + weighted pocket contact maps",
               "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "thresholds_a": list(THRESHOLDS_A),
               "weighted": f"exp(-d/{WEIGHT_SCALE_A} A) within {WEIGHT_CUTOFF_A} A, else 0",
               "receptors": {}}
    for sym in all_symbols():
        z = np.load(os.path.join(FEATURE_DIR, f"{sym}_distances.npz"))
        hm = z["heavy_min_matrix"].astype(float)
        np.fill_diagonal(hm, 0.0)
        maps = {f"contact_{int(t)}": (hm <= t).astype(np.uint8) for t in THRESHOLDS_A}
        weighted = np.where(hm <= WEIGHT_CUTOFF_A,
                            np.exp(-hm / WEIGHT_SCALE_A), 0.0).astype(np.float32)
        out = os.path.join(FEATURE_DIR, f"{sym}_contacts.npz")
        np.savez_compressed(out, weighted=weighted, **maps)
        n = hm.shape[0]
        summary["receptors"][sym] = {
            "n_pocket_residues": n,
            "n_contacts_4": int(maps["contact_4"].sum() // 2),
            "n_contacts_6": int(maps["contact_6"].sum() // 2),
            "n_contacts_8": int(maps["contact_8"].sum() // 2),
            "file": f"{sym}_contacts.npz",
        }
        print(f"{sym:8} n={n:3}  contacts 4/6/8 A = "
              f"{summary['receptors'][sym]['n_contacts_4']}/"
              f"{summary['receptors'][sym]['n_contacts_6']}/"
              f"{summary['receptors'][sym]['n_contacts_8']}", flush=True)
    save_json(summary, "paper2/data/features/phase12_summary.json")
    print("wrote", FEATURE_DIR)


if __name__ == "__main__":
    main()
