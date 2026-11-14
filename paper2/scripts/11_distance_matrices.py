"""Phase 11 - Pocket distance matrices.

For each receptor's Phase 7/8 pocket: C-alpha pairwise distance matrix and
heavy-atom minimum-distance matrix (residue x residue), aligned to the Phase 8
mapping order (sorted by UniProt position). Pure numpy.

Output: paper2/data/features/{SYM}_distances.npz with keys
  ca_matrix [n, n] (A), heavy_min_matrix [n, n] (A),
  auth_seq_id [n] (str), uniprot_pos [n], esm2_residue_index_0based [n]

Run:  python3 paper2/scripts/11_distance_matrices.py
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage2_common import (FEATURE_DIR, all_symbols, ca_coords, pocket_residues,
                           residue_heavy_coords, save_json, structure_atoms)


def main():
    os.makedirs(FEATURE_DIR, exist_ok=True)
    summary = {"phase": 11, "purpose": "pocket CA + heavy-atom min distance matrices",
               "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "order": "pocket residues sorted by UniProt position (Phase 8)",
               "receptors": {}}
    for sym in all_symbols():
        residues = pocket_residues(sym)
        cas = ca_coords(sym)
        _, atoms, _ = structure_atoms(sym)
        heavy = residue_heavy_coords(atoms)

        missing_ca = [r["auth_seq_id"] for r in residues if r["auth_seq_id"] not in cas]
        if missing_ca:
            raise SystemExit(f"{sym}: pocket residues without CA: {missing_ca[:5]}")

        ca_pts = np.stack([cas[r["auth_seq_id"]] for r in residues])
        ca_matrix = np.linalg.norm(ca_pts[:, None, :] - ca_pts[None, :, :], axis=-1)

        n = len(residues)
        hm = np.full((n, n), np.inf)
        for i, r1 in enumerate(residues):
            _, c1 = heavy[r1["auth_seq_id"]]
            for j in range(i, n):
                _, c2 = heavy[residues[j]["auth_seq_id"]]
                d = np.sqrt(((c1[:, None, :] - c2[None, :, :]) ** 2).sum(-1)).min()
                hm[i, j] = hm[j, i] = d

        out = os.path.join(FEATURE_DIR, f"{sym}_distances.npz")
        np.savez_compressed(
            out,
            ca_matrix=ca_matrix.astype(np.float32),
            heavy_min_matrix=hm.astype(np.float32),
            auth_seq_id=np.array([r["auth_seq_id"] for r in residues]),
            uniprot_pos=np.array([r["uniprot_pos"] for r in residues]),
            esm2_residue_index_0based=np.array([r["esm2_residue_index_0based"]
                                                for r in residues]),
        )
        summary["receptors"][sym] = {
            "n_pocket_residues": n,
            "ca_matrix_mean_a": round(float(ca_matrix[np.triu_indices(n, 1)].mean()), 2),
            "heavy_min_max_a": round(float(hm.max()), 2),
            "file": f"{sym}_distances.npz",
        }
        print(f"{sym:8} n={n:3}  ca_mean={summary['receptors'][sym]['ca_matrix_mean_a']:6.2f} A  "
              f"heavy_min_max={summary['receptors'][sym]['heavy_min_max_a']:5.1f} A", flush=True)
    save_json(summary, "paper2/data/features/phase11_summary.json")
    print("wrote", FEATURE_DIR)


if __name__ == "__main__":
    main()
