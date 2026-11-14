"""Shared Stage 2 helpers: pocket context per receptor (structure atoms,
CA/heavy-atom coordinates, ESM-2 residue embeddings, pLDDT).

All inputs are frozen artefacts: Phase 7/8 outputs under
paper2/data/structures/, Paper 1 residue embeddings
(data/real/residue_embeddings_expanded.npz), and Phase 6 pLDDT.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mmcif_lite import atom_rows, het_rows, parse_atom_site

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
STRUCT_DIR = os.path.join(REPO, "paper2", "data", "structures")
FEATURE_DIR = os.path.join(REPO, "paper2", "data", "features")

AA20 = "ACDEFGHIKLMNPQRSTVWY"
AA_INDEX = {aa: i for i, aa in enumerate(AA20)}


def load_json(rel):
    with open(os.path.join(REPO, rel)) as f:
        return json.load(f)


def save_json(obj, rel):
    path = os.path.join(REPO, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)
    return path


def all_symbols():
    return sorted(load_json(os.path.join("paper2", "data", "structures",
                                         "residue_mapping.json"))["receptors"])


def pocket_residues(sym):
    """Ordered pocket residue records from Phase 8 (sorted by UniProt pos)."""
    rec = load_json(os.path.join("paper2", "data", "structures",
                                 "residue_mapping.json"))["receptors"][sym]
    return sorted(rec["mapping"], key=lambda r: r["uniprot_pos"])


def structure_atoms(sym):
    """(receptor_chain, receptor_atoms, ligand_atoms) for the primary structure;
    ligand restricted to the chosen co-crystallized copy (label_asym_id)."""
    rec = load_json(os.path.join("paper2", "data", "structures",
                                 "pockets_defined.json"))["receptors"][sym]
    tags, rows = parse_atom_site(os.path.join(STRUCT_DIR, f"{rec['pdb_id']}.cif"))
    atoms = [a for a in atom_rows(tags, rows)
             if a["auth_asym"] == rec["receptor_chain"] and a["element"].upper() != "H"]
    copy = rec["ligand"].get("copy")
    lig = [h for h in het_rows(tags, rows)
           if h["comp_id"] == rec["ligand"]["comp_id"]
           and h["element"].upper() != "H"
           and (copy is None or h["label_asym"] == copy)]
    return rec["receptor_chain"], atoms, lig


def residue_heavy_coords(atoms):
    """auth_seq_id -> (resname, np.ndarray [n_atoms, 3])."""
    per = {}
    for a in atoms:
        per.setdefault(a["auth_seq"], [a["comp_id"], []])[1].append((a["x"], a["y"], a["z"]))
    return {k: (v[0], np.asarray(v[1], dtype=float)) for k, v in per.items()}


def ca_coords(sym):
    """auth_seq_id -> np.array([x, y, z]) of the first CA atom."""
    _, atoms, _ = structure_atoms(sym)
    out = {}
    for a in atoms:
        if a["atom"] == "CA" and a["auth_seq"] not in out:
            out[a["auth_seq"]] = np.array([a["x"], a["y"], a["z"]])
    return out


def esm2_embeddings(sym):
    """Full per-residue ESM-2 matrix [seq_len, 1280]; row i = UniProt pos i+1."""
    z = np.load(os.path.join(REPO, "data", "real", "residue_embeddings_expanded.npz"),
                allow_pickle=True)
    return z[f"{sym}_residues"]


def plddt_by_pos(sym):
    """UniProt 1-based position -> pLDDT (float) from Phase 6."""
    rec = load_json(os.path.join("paper2", "data", "structures", "afdb",
                                 "afdb_models.json"))["receptors"][sym]
    return {int(k): v for k, v in rec["plddt"].items()}


def one_hot(resname1):
    v = np.zeros(len(AA20), dtype=np.float32)
    v[AA_INDEX.get(resname1, AA_INDEX["A"])] = 1.0
    return v
