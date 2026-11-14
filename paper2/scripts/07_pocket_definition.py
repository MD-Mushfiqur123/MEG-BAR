"""Phase 7 - Orthosteric pocket definition from reference structures.

Downloads the primary mmCIF for each of the 11 receptors (from
paper2/data/structures/pdb_selection.json), identifies the receptor chain by
aligning each chain's sequence to the UniProt sequence, then defines the
pocket around each candidate co-crystallized ligand (heavy atoms within
6.5 A). The ligand whose pocket best overlaps the Paper 1 annotated pocket
residues (UniProt numbering, data/real/pockets.json) is chosen as the
orthosteric ligand. Residues from other chains near the ligand are stored as
interface metadata (relevant for the GABRA1 pentamer).

Output: paper2/data/structures/pockets_defined.json

Run:  python3 paper2/scripts/07_pocket_definition.py
"""

import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mmcif_lite import (AA3TO1, ANCHOR_RESIDUES, alignment_identity, atom_rows,
                        het_rows, nw_align, parse_atom_site)

POCKET_RADIUS_A = 6.5
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
STRUCT_DIR = os.path.join(REPO, "paper2", "data", "structures")
RCSB_CIF = "https://files.rcsb.org/download/{pdb}.cif"


def fetch(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MEG-BAR-paper2/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


ANCHORS = ANCHOR_RESIDUES


def load_json(rel):
    with open(os.path.join(REPO, rel)) as f:
        return json.load(f)


def dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def chain_residue_coords(atoms, chain):
    """auth_seq_id -> [resname, [(x, y, z), ...]] for one chain."""
    per = {}
    for a in atoms:
        if a["auth_asym"] != chain or a["element"].upper() == "H":
            continue
        e = per.setdefault(a["auth_seq"], [a["comp_id"], []])
        e[1].append((a["x"], a["y"], a["z"]))
    return per


def ligand_copies(hets, comp_id):
    """label_asym_id -> heavy atoms, one dict entry per co-crystallized copy."""
    out = {}
    for h in hets:
        if h["comp_id"].upper() == comp_id.upper() and h["element"].upper() != "H":
            out.setdefault(h["label_asym"], []).append(h)
    return out


def pocket_for_ligand(res_coords, ligs, radius=POCKET_RADIUS_A):
    """auth_seq_id set of residues with any heavy atom within radius of ligand."""
    r2 = radius * radius
    hits = set()
    for res_id, (_, coords) in res_coords.items():
        for c in coords:
            if any(dist2(c, (l["x"], l["y"], l["z"])) <= r2 for l in ligs):
                hits.add(res_id)
                break
    return hits


def chain_sequence(atoms, chain):
    seq, seen = [], set()
    for a in atoms:
        if a["auth_asym"] != chain:
            continue
        aa = AA3TO1.get(a["comp_id"].upper())
        if aa is None or a["auth_seq"] in seen:
            continue
        seen.add(a["auth_seq"])
        seq.append(aa)
    return "".join(seq)


def find_receptor_chain(atoms, uniprot_seq):
    """Return (chain, identity, coverage) of the best UniProt match."""
    best = (None, -1.0, 0.0)
    for ch in sorted({a["auth_asym"] for a in atoms}):
        seq = chain_sequence(atoms, ch)
        if len(seq) < 50:
            continue
        ident, npairs = alignment_identity(seq, uniprot_seq)
        cov = npairs / len(uniprot_seq)
        score = ident * min(1.0, cov / 0.5)
        if score > best[1]:
            best = (ch, ident, cov)
    return best


def map_auth_to_uniprot(atoms, chain, uniprot_seq):
    """auth_seq_id -> UniProt 1-based position via NW alignment."""
    seq, auth_ids, seen = [], [], set()
    for a in atoms:
        if a["auth_asym"] != chain:
            continue
        aa = AA3TO1.get(a["comp_id"].upper())
        if aa is None or a["auth_seq"] in seen:
            continue
        seen.add(a["auth_seq"])
        seq.append(aa)
        auth_ids.append(a["auth_seq"])
    pairs = nw_align("".join(seq), uniprot_seq)
    return {auth_ids[i]: j + 1 for i, j in pairs}, "".join(seq)


def other_chain_interface(atoms, chain, ligs):
    """Residues on other chains within 6.5 A of the chosen ligand."""
    r2 = POCKET_RADIUS_A * POCKET_RADIUS_A
    other = {}
    for a in atoms:
        if a["auth_asym"] == chain or a["element"].upper() == "H":
            continue
        other.setdefault(a["auth_asym"], {}).setdefault(
            a["auth_seq"], [a["comp_id"], []])[1].append((a["x"], a["y"], a["z"]))
    out = {}
    for ch, per in other.items():
        for res_id, (resname, coords) in per.items():
            if any(dist2(c, (l["x"], l["y"], l["z"])) <= r2 for c in coords for l in ligs):
                out.setdefault(ch, []).append({"auth_seq_id": res_id, "residue": resname})
    return {ch: sorted(v, key=lambda r: r["auth_seq_id"]) for ch, v in out.items()}


def main():
    sel = load_json(os.path.join("paper2", "data", "structures", "pdb_selection.json"))
    proteins = load_json(os.path.join("data", "real", "proteins_expanded.json"))
    paper1_pockets = load_json(os.path.join("data", "real", "pockets.json"))["receptors"]

    result = {
        "purpose": "Paper 2 Phase 7 - orthosteric pockets from reference structures",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pocket_radius_a": POCKET_RADIUS_A,
        "selection_rule": ("if Paper 1 pocket annotation exists: ligand copy whose 6.5 A "
                           "pocket maximizes overlap with it (UniProt numbering); otherwise "
                           "the ligand copy whose pocket contains the conserved anchor "
                           "residue (Asp3.32 / SERT D98 / DAT D79); copies scored "
                           "individually so multi-protomer entries pick one site"),
        "receptors": {},
    }

    for sym, info in sel["receptors"].items():
        primary = info["primary"]
        pdb_id = primary["pdb_id"]
        acc = info["uniprot"]
        uniprot_seq = proteins[sym]["sequence"]
        p1_pocket = set(paper1_pockets.get(sym, {}).get("pocket_residues_1based") or [])

        cif_path = os.path.join(STRUCT_DIR, f"{pdb_id}.cif")
        if not os.path.exists(cif_path):
            data = fetch(RCSB_CIF.format(pdb=pdb_id))
            with open(cif_path, "wb") as f:
                f.write(data)
            time.sleep(0.2)

        tags, rows = parse_atom_site(cif_path)
        atoms = list(atom_rows(tags, rows))
        hets = list(het_rows(tags, rows))
        chain, ident, cov = find_receptor_chain(atoms, uniprot_seq)
        if chain is None:
            raise SystemExit(f"{sym}: no receptor chain found in {pdb_id}")

        res_coords = chain_residue_coords(atoms, chain)
        auth_to_uniprot, chain_seq = map_auth_to_uniprot(atoms, chain, uniprot_seq)

        scored = []
        anchor = ANCHORS.get(sym)
        for lig in primary["ligands"]:
            comp = lig["comp_id"]
            for copy_id, ligs in sorted(ligand_copies(hets, comp).items()):
                pocket_auth = pocket_for_ligand(res_coords, ligs)
                mapped = {auth_to_uniprot[a] for a in pocket_auth if a in auth_to_uniprot}
                overlap = sum(1 for p in mapped if p in p1_pocket)
                anchor_hit = bool(anchor) and any(p == anchor[0] for p in mapped)
                scored.append({
                    "comp_id": comp,
                    "copy": copy_id,
                    "name": lig["name"],
                    "n_ligand_atoms": len(ligs),
                    "n_pocket_residues": len(pocket_auth),
                    "n_mapped_to_uniprot": len(mapped),
                    "overlap_with_paper1_pocket": overlap,
                    "frac_of_paper1_pocket": round(overlap / len(p1_pocket), 4) if p1_pocket else 0.0,
                    "contains_anchor": anchor_hit,
                })
        if not scored:
            raise SystemExit(f"{sym}: no candidate ligand atoms found in {pdb_id}")
        if anchor:
            rule = f"anchor_first_{anchor[1]}{anchor[0]}"
            if p1_pocket:
                rule += "+paper1_pocket_overlap"
            scored.sort(key=lambda s: (not s["contains_anchor"],
                                       -s["overlap_with_paper1_pocket"],
                                       -s["frac_of_paper1_pocket"], s["comp_id"]))
        elif p1_pocket:
            rule = "paper1_pocket_overlap"
            scored.sort(key=lambda s: (-s["overlap_with_paper1_pocket"],
                                       -s["frac_of_paper1_pocket"], s["comp_id"]))
        else:
            rule = "largest_pocket"
            scored.sort(key=lambda s: (-s["n_pocket_residues"], s["comp_id"]))
        chosen = scored[0]

        ligs = ligand_copies(hets, chosen["comp_id"])[chosen["copy"]]
        pocket_auth = pocket_for_ligand(res_coords, ligs)
        pocket_records = []
        for a in sorted(pocket_auth, key=lambda x: int(x) if x.isdigit() else 0):
            up = auth_to_uniprot.get(a)
            pocket_records.append({
                "auth_seq_id": a,
                "uniprot_pos": up,
                "residue": res_coords[a][0],
            })
        interface = other_chain_interface(atoms, chain, ligs)

        result["receptors"][sym] = {
            "uniprot": acc,
            "pdb_id": pdb_id,
            "receptor_chain": chain,
            "chain_length_in_structure": len(chain_seq),
            "chain_alignment_identity": round(ident, 4),
            "chain_alignment_coverage": round(cov, 4),
            "selection_rule": rule,
            "ligand": chosen,
            "ligand_scores": scored,
            "n_pocket_residues": len(pocket_records),
            "pocket_residues": pocket_records,
            "interface_other_chains": interface,
        }
        print(f"{sym:8} {pdb_id} chain={chain} ident={ident:.2f} cov={cov:.2f} "
              f"ligand={chosen['comp_id']} pocket={len(pocket_records)} "
              f"overlap={chosen['overlap_with_paper1_pocket']}/{len(p1_pocket)}", flush=True)

    out = os.path.join(STRUCT_DIR, "pockets_defined.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
