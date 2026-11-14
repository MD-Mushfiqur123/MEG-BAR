"""Phase 8 - Residue mapping: structure pocket -> UniProt -> ESM-2 token index.

Maps each pocket residue in pockets_defined.json (auth_seq_id within the
reference structure) onto UniProt 1-based positions via the NW alignment
stored during Phase 7, then onto the 0-based ESM-2 residue index used by
Paper 1's frozen embeddings (esm2_residue_index_0based = uniprot_pos - 1).

Exit criteria (asserted):
- 0 unmapped pocket residues across all 11 receptors
- canonical anchor residues present in every mapped pocket for the
  8 aminergic GPCRs (D3.32 from the DRY motif: DRD2 D114, DRD3 D110,
  HTR1A D116, HTR2A D155, CHRM1 D105, ADRA2A D128, ADRB2 D113, HRH1 D107)
  + SERT (D98) + DAT (D79); GABRA1 has no anchor.

Output: paper2/data/structures/residue_mapping.json

Run:  python3 paper2/scripts/08_residue_mapping.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mmcif_lite import AA3TO1, ANCHOR_RESIDUES

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
STRUCT_DIR = os.path.join(REPO, "paper2", "data", "structures")

ANCHORS = ANCHOR_RESIDUES


def load_json(rel):
    with open(os.path.join(REPO, rel)) as f:
        return json.load(f)


def main():
    pockets = load_json(os.path.join("paper2", "data", "structures", "pockets_defined.json"))
    proteins = load_json(os.path.join("data", "real", "proteins_expanded.json"))
    paper1_pockets = load_json(os.path.join("data", "real", "pockets.json"))["receptors"]

    result = {
        "purpose": "Paper 2 Phase 8 - pocket residue -> UniProt -> ESM-2 token mapping",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "esm2_index_convention": ("esm2_residue_index_0based = uniprot_pos - 1 "
                                  "(0-based index into the full UniProt sequence)"),
        "receptors": {},
    }
    total_unmapped = 0
    anchor_failures = []

    for sym, rec in pockets["receptors"].items():
        uniprot_seq = proteins[sym]["sequence"]
        p1_set = set(paper1_pockets.get(sym, {}).get("pocket_residues_1based") or [])

        mapped, unmapped = [], []
        for pr in rec["pocket_residues"]:
            up = pr["uniprot_pos"]
            if up is None or up < 1 or up > len(uniprot_seq):
                unmapped.append(pr)
                continue
            aa1 = AA3TO1.get(pr["residue"].upper(), "X")
            wt = uniprot_seq[up - 1]
            mapped.append({
                "auth_seq_id": pr["auth_seq_id"],
                "uniprot_pos": up,
                "uniprot_residue": wt,
                "structure_residue": aa1,
                "esm2_residue_index_0based": up - 1,
                "in_paper1_pocket": up in p1_set,
                "matches_uniprot": aa1 == wt,
            })
        total_unmapped += len(unmapped)

        anchor = ANCHORS.get(sym)
        anchor_ok = None
        if anchor:
            pos, res = anchor
            anchor_ok = any(m["uniprot_pos"] == pos and m["uniprot_residue"] == res
                            for m in mapped)
            if not anchor_ok:
                anchor_failures.append(f"{sym}: anchor {res}{pos} not in mapped pocket")

        idx = sorted(m["esm2_residue_index_0based"] for m in mapped)
        result["receptors"][sym] = {
            "uniprot": rec["uniprot"],
            "pdb_id": rec["pdb_id"],
            "receptor_chain": rec["receptor_chain"],
            "n_pocket_residues": len(rec["pocket_residues"]),
            "n_mapped": len(mapped),
            "n_unmapped": len(unmapped),
            "unmapped": unmapped,
            "n_in_paper1_pocket": sum(1 for m in mapped if m["in_paper1_pocket"]),
            "n_mismatches_vs_uniprot": sum(1 for m in mapped if not m["matches_uniprot"]),
            "anchor": {"position": anchor[0], "residue": anchor[1], "present": anchor_ok}
            if anchor else None,
            "esm2_residue_indices_0based": idx,
            "mapping": mapped,
        }
        print(f"{sym:8} mapped={len(mapped):3} unmapped={len(unmapped)} "
              f"paper1_overlap={result['receptors'][sym]['n_in_paper1_pocket']:3} "
              f"anchor={'OK' if anchor_ok else ('n/a' if not anchor else 'MISSING')}",
              flush=True)

    result["totals"] = {
        "n_receptors": len(result["receptors"]),
        "total_unmapped": total_unmapped,
        "anchor_failures": anchor_failures,
    }
    assert total_unmapped == 0, f"{total_unmapped} unmapped pocket residues"
    assert not anchor_failures, f"anchor failures: {anchor_failures}"

    out = os.path.join(STRUCT_DIR, "residue_mapping.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
