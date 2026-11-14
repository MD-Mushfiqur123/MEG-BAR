"""Phase 13 - Pocket residue graphs.

Nodes = pocket residues (Phase 8 order). Node features = [ESM-2 per-residue
embedding (1280, from Paper 1's frozen residue embeddings at the Phase 8
token index), residue-identity one-hot (20), AFDB pLDDT (1)] -> 1301 dims.
Edges = heavy-atom min distance <= 8 A (Phase 11 matrix); edge feature = the
distance in A. Stored as framework-neutral numpy .npz (CI installs numpy only;
torch/PyG are not available there - documented plan deviation).

Output: paper2/data/features/{SYM}_graph.npz with keys
  x [n, 1301] float32, edge_index [2, e] int32, edge_attr [e] float32,
  aa_onehot_index [n] int8, plddt [n], uniprot_pos [n],
  esm2_residue_index_0based [n]

Run:  python3 paper2/scripts/13_pocket_graphs.py
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage2_common import (FEATURE_DIR, AA_INDEX, all_symbols, esm2_embeddings,
                           one_hot, pocket_residues, plddt_by_pos, save_json)

EDGE_CUTOFF_A = 8.0


def main():
    summary = {"phase": 13, "purpose": "pocket residue graphs (numpy npz)",
               "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "node_features": "ESM-2 1280 + AA one-hot 20 + pLDDT 1 = 1301",
               "edge_rule": f"heavy-atom min distance <= {EDGE_CUTOFF_A} A",
               "receptors": {}}
    for sym in all_symbols():
        residues = pocket_residues(sym)
        emb = esm2_embeddings(sym)
        plddt = plddt_by_pos(sym)
        z = np.load(os.path.join(FEATURE_DIR, f"{sym}_distances.npz"))
        hm = z["heavy_min_matrix"].astype(float)
        np.fill_diagonal(hm, 0.0)

        feats, aa_idx, pld = [], [], []
        for r in residues:
            e = emb[r["esm2_residue_index_0based"]].astype(np.float32)
            feats.append(np.concatenate([e, one_hot(r["uniprot_residue"]),
                                         [plddt[r["uniprot_pos"]]]]))
            aa_idx.append(AA_INDEX.get(r["uniprot_residue"], 0))
            pld.append(plddt[r["uniprot_pos"]])
        x = np.stack(feats).astype(np.float32)

        iu, ju = np.where(np.triu(hm <= EDGE_CUTOFF_A, k=1))
        edge_index = np.stack([iu, ju]).astype(np.int32)
        edge_attr = hm[iu, ju].astype(np.float32)

        out = os.path.join(FEATURE_DIR, f"{sym}_graph.npz")
        np.savez_compressed(
            out, x=x, edge_index=edge_index, edge_attr=edge_attr,
            aa_onehot_index=np.array(aa_idx, dtype=np.int8),
            plddt=np.array(pld, dtype=np.float32),
            uniprot_pos=z["uniprot_pos"],
            esm2_residue_index_0based=z["esm2_residue_index_0based"],
        )
        summary["receptors"][sym] = {
            "n_nodes": int(x.shape[0]),
            "n_edges": int(edge_index.shape[1]),
            "x_dim": int(x.shape[1]),
            "mean_plddt": round(float(np.mean(pld)), 2),
            "file": f"{sym}_graph.npz",
        }
        print(f"{sym:8} nodes={x.shape[0]:3}  edges={edge_index.shape[1]:4}  "
              f"x_dim={x.shape[1]}  mean_pLDDT={np.mean(pld):5.1f}", flush=True)
    save_json(summary, "paper2/data/features/phase13_summary.json")
    print("wrote", FEATURE_DIR)


if __name__ == "__main__":
    main()
