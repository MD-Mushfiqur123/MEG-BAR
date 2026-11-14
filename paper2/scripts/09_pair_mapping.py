"""Phase 9 - Ligand-pair mapping: join Paper 1's frozen ChEMBL pairs onto the
11 receptor structures.

Reproduces Paper 1's exact pair construction from the frozen raw records
(data/real/raw_activities_expanded.csv): keep rows with measured pChEMBL and
SMILES, then deduplicate to one pair per (gene, molecule_chembl_id) using the
median pChEMBL - yielding the 41,271 pairs cited in the Paper 2 title. Each
pair is annotated with its document year (temporal split) and with the 3D
pocket metadata from Phase 7/8 (reference PDB, chain, pocket residue count,
ESM-2 residue indices availability).

Outputs:
- paper2/data/structures/pairs_41271.csv  (frozen pair table)
- paper2/data/structures/ligand_pair_mapping.json  (coverage + exclusions)

Run:  python3 paper2/scripts/09_pair_mapping.py
"""

import csv
import json
import os
import time

import pandas as pd

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
STRUCT_DIR = os.path.join(REPO, "paper2", "data", "structures")


def load_json(rel):
    with open(os.path.join(REPO, rel)) as f:
        return json.load(f)


def main():
    raw = pd.read_csv(os.path.join(REPO, "data", "real", "raw_activities_expanded.csv"))
    n_raw = len(raw)

    raw["pchembl_value"] = pd.to_numeric(raw["pchembl_value"], errors="coerce")
    df = raw.dropna(subset=["pchembl_value", "smiles"])
    n_after_dropna = len(df)
    df = df.copy()
    df["document_year"] = df["document_chembl_id"].astype(str).map(
        load_json(os.path.join(REPO, "data", "real", "document_years.json")))
    n_with_year = int(df["document_year"].notna().sum())

    agg = (df.groupby(["gene", "molecule_chembl_id"], as_index=False)
             .agg(pchembl_median=("pchembl_value", "median"),
                  smiles=("smiles", "first"),
                  document_year=("document_year", "median"),
                  n_records=("pchembl_value", "size"),
                  n_documents=("document_chembl_id", "nunique")))
    n_pairs = len(agg)

    pockets = load_json(os.path.join("paper2", "data", "structures", "pockets_defined.json"))
    mapping = load_json(os.path.join("paper2", "data", "structures", "residue_mapping.json"))

    per_receptor = {}
    for sym, rec in pockets["receptors"].items():
        n_pocket = rec["n_pocket_residues"]
        n_esm = len(mapping["receptors"][sym]["esm2_residue_indices_0based"])
        sub = agg[agg.gene == sym]
        yr = sub["document_year"].dropna()
        per_receptor[sym] = {
            "uniprot": rec["uniprot"],
            "pdb_id": rec["pdb_id"],
            "receptor_chain": rec["receptor_chain"],
            "orthosteric_ligand": rec["ligand"]["comp_id"],
            "n_pocket_residues": n_pocket,
            "n_esm2_indices": n_esm,
            "pocket_grounding_available": bool(n_esm > 0),
            "n_pairs": int(len(sub)),
            "n_unique_ligands": int(sub["molecule_chembl_id"].nunique()),
            "n_pairs_with_year": int(yr.notna().sum()),
            "n_pairs_pre2015": int((yr < 2015).sum()),
            "n_pairs_2015plus": int((yr >= 2015).sum()),
            "pchembl_median_range": [round(float(sub["pchembl_median"].min()), 2),
                                     round(float(sub["pchembl_median"].max()), 2)],
        }

    agg["pocket_pdb_id"] = agg["gene"].map(lambda g: pockets["receptors"][g]["pdb_id"])
    agg["pocket_chain"] = agg["gene"].map(lambda g: pockets["receptors"][g]["receptor_chain"])
    agg["n_pocket_residues"] = agg["gene"].map(
        lambda g: pockets["receptors"][g]["n_pocket_residues"])

    cols = ["gene", "molecule_chembl_id", "pchembl_median", "smiles",
            "document_year", "n_records", "n_documents",
            "pocket_pdb_id", "pocket_chain", "n_pocket_residues"]
    out_csv = os.path.join(STRUCT_DIR, "pairs_41271.csv")
    agg[cols].to_csv(out_csv, index=False)

    summary = {
        "purpose": "Paper 2 Phase 9 - frozen ChEMBL pairs joined onto receptor structures",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pair_construction": ("identical to Paper 1 scripts/real/03_experiment.py: "
                              "measured pChEMBL + SMILES present, median per "
                              "(gene, molecule_chembl_id)"),
        "totals": {
            "raw_records": n_raw,
            "records_after_dropna": n_after_dropna,
            "records_collapsed_by_dedup": n_after_dropna - n_pairs,
            "pairs": n_pairs,
            "records_with_document_year": n_with_year,
            "pairs_with_3d_pocket": int(sum(v["n_pairs"] for v in per_receptor.values()
                                            if v["pocket_grounding_available"])),
            "pairs_without_3d_pocket": int(sum(v["n_pairs"] for v in per_receptor.values()
                                               if not v["pocket_grounding_available"])),
        },
        "exclusions": [
            "rows without measured pChEMBL or SMILES (dropna)",
            "duplicate (gene, molecule) records collapsed by median pChEMBL",
        ],
        "per_receptor": per_receptor,
        "pairs_csv": "pairs_41271.csv",
    }
    out_json = os.path.join(STRUCT_DIR, "ligand_pair_mapping.json")
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=1)

    print(f"raw={n_raw} -> pairs={n_pairs} (collapsed {n_after_dropna - n_pairs})")
    for sym, v in per_receptor.items():
        print(f"{sym:8} pairs={v['n_pairs']:5}  pocket={v['n_pocket_residues']:3} res "
              f"pre2015={v['n_pairs_pre2015']:5} 2015+={v['n_pairs_2015plus']:5} "
              f"pdb={v['pdb_id']}")
    print("wrote", out_csv)
    print("wrote", out_json)


if __name__ == "__main__":
    main()
