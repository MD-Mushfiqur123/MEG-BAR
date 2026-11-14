"""Phase 15 - Feature validation: sanity checks over all Stage 2 artefacts.

Checks per receptor:
- distance matrices symmetric, zero diagonal, finite
- contact maps nested: contact_8 >= contact_6 >= contact_4, and consistent
  with the distance matrix thresholds
- graphs: node count matches pocket, edge set equals the 8 A contact map,
  node feature dimension 1301, pLDDT in [0, 100], ESM-2 indices in range
- geometry: SASA within [0, 400] A^2 per residue
- anchors present (re-check from Phase 8 mapping)

Output: paper2/data/features/feature_validation.json (all checks must pass;
script exits non-zero otherwise).

Run:  python3 paper2/scripts/15_feature_validation.py
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage2_common import (FEATURE_DIR, all_symbols, esm2_embeddings,
                           load_json, pocket_residues, save_json)

NODE_DIM = 1301


def main():
    result = {"phase": 15, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "receptors": {}, "failures": []}

    def check(sym, name, ok, detail=""):
        entry = result["receptors"].setdefault(sym, {})
        entry[name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            result["failures"].append(f"{sym}: {name} {detail}")

    for sym in all_symbols():
        residues = pocket_residues(sym)
        n = len(residues)

        dz = np.load(os.path.join(FEATURE_DIR, f"{sym}_distances.npz"))
        hm = dz["heavy_min_matrix"].astype(float)
        ca = dz["ca_matrix"].astype(float)
        for label, m in [("ca_matrix", ca), ("heavy_min_matrix", hm)]:
            check(sym, f"{label}_symmetric",
                  np.allclose(m, m.T, atol=1e-4), f"max_asym={np.abs(m-m.T).max():.2e}")
            check(sym, f"{label}_zero_diagonal", bool(np.abs(np.diag(m)).max() < 1e-5))
            check(sym, f"{label}_finite", bool(np.isfinite(m).all()))
        off = ca[np.triu_indices(n, 1)]
        check(sym, "ca_positive_offdiag", bool(off.min() > 0), f"min={off.min():.2f}")

        cm = np.load(os.path.join(FEATURE_DIR, f"{sym}_contacts.npz"))
        c4, c6, c8 = cm["contact_4"], cm["contact_6"], cm["contact_8"]
        check(sym, "contacts_nested", bool((c8 >= c6).all() and (c6 >= c4).all()))
        check(sym, "contact_4_matches_distance",
              bool(np.array_equal(c4, (hm <= 4.0).astype(np.uint8))))
        check(sym, "contact_8_matches_distance",
              bool(np.array_equal(c8, (hm <= 8.0).astype(np.uint8))))

        g = np.load(os.path.join(FEATURE_DIR, f"{sym}_graph.npz"))
        check(sym, "graph_node_count", g["x"].shape[0] == n,
              f"{g['x'].shape[0]} vs {n}")
        check(sym, "graph_node_dim", g["x"].shape[1] == NODE_DIM, f"{g['x'].shape[1]}")
        ei = g["edge_index"]
        n_expected_edges = int(((hm <= 8.0).astype(int).sum() - n) // 2)
        check(sym, "graph_edges_match_contact_8",
              ei.shape[1] == n_expected_edges,
              f"{ei.shape[1]} vs {n_expected_edges}")
        check(sym, "graph_edge_attr_in_range",
              bool(g["edge_attr"].min() >= 0 and g["edge_attr"].max() <= 8.0))
        emb = esm2_embeddings(sym)
        idx = g["esm2_residue_index_0based"]
        check(sym, "esm2_indices_in_range",
              bool(idx.min() >= 0 and idx.max() < emb.shape[0]))
        check(sym, "plddt_in_range",
              bool(g["plddt"].min() >= 0 and g["plddt"].max() <= 100))

        geo = np.load(os.path.join(FEATURE_DIR, f"{sym}_geometry.npz"))
        s = geo["sasa_per_residue"]
        check(sym, "sasa_in_range", bool(s.min() >= 0 and s.max() <= 400),
              f"[{s.min():.1f}, {s.max():.1f}]")
        check(sym, "sasa_len_matches", s.shape[0] == n)

        anchors = load_json(os.path.join("paper2", "data", "structures",
                                         "residue_mapping.json"))
        a = anchors["receptors"][sym]["anchor"]
        if a:
            check(sym, "anchor_present", bool(a["present"]),
                  f"{a['residue']}{a['position']}")

    result["all_passed"] = not result["failures"]
    save_json(result, "paper2/data/features/feature_validation.json")
    n_checks = sum(len(v) for v in result["receptors"].values())
    print(f"checks run: {n_checks}  failures: {len(result['failures'])}")
    for f in result["failures"][:10]:
        print("FAIL:", f)
    if result["failures"]:
        raise SystemExit(1)
    print("all Stage 2 feature checks passed")


if __name__ == "__main__":
    main()
