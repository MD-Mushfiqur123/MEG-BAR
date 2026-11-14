"""Phase 14 - Pocket geometric descriptors (pure numpy).

Per receptor pocket:
- volume + surface area by 0.5 A voxelization of the 6.5 A ligand shell,
  excluding voxels inside any protein heavy-atom van der Waals sphere
- sphericity = pi^(1/3) * (6V)^(2/3) / A (1 for a perfect sphere)
- pocket radius = max CA distance from the ligand centroid
- pocket depth = max distance from the ligand centroid to a pocket voxel
- per-residue solvent accessibility (Shrake-Rupley SASA, 92 points,
  1.4 A probe) over all protein heavy atoms; reported for pocket residues

Output: paper2/data/features/{SYM}_geometry.npz (sasa_per_residue [n]) and
paper2/data/features/phase14_summary.json (scalars).

Run:  python3 paper2/scripts/14_geometric_descriptors.py
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mmcif_lite import atom_rows, het_rows, parse_atom_site
from stage2_common import (FEATURE_DIR, STRUCT_DIR, all_symbols, ca_coords,
                           load_json, pocket_residues, save_json, structure_atoms)

VOXEL_A = 0.5
POCKET_RADIUS_A = 6.5
PROBE_A = 1.4
N_SPHERE_POINTS = 92
VDW = {"C": 1.70, "N": 1.55, "O": 1.52, "S": 1.80, "P": 1.80,
       "SE": 1.90, "MG": 1.20, "ZN": 1.20, "CA": 1.20, "NA": 1.20, "K": 1.20}


def sphere_points(n):
    i = np.arange(0, n, dtype=float) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(theta) * np.sin(phi),
                     np.sin(theta) * np.sin(phi),
                     np.cos(phi)], axis=1)


def shrink_rupley(coords, radii, pts):
    n = len(coords)
    out = np.zeros(n)
    for i in range(n):
        test = coords[i] + radii[i] * pts
        d = np.linalg.norm(coords - coords[i], axis=1)
        occ = np.where(d < radii + radii[i])[0]
        occ = occ[occ != i]
        if len(occ):
            diff = test[:, None, :] - coords[occ][None, :, :]
            blocked = ((diff ** 2).sum(-1) <= radii[occ][None, :] ** 2).any(1)
            ok = ~blocked
        else:
            ok = np.ones(len(test), dtype=bool)
        out[i] = 4 * np.pi * radii[i] ** 2 * ok.mean()
    return out


def pocket_voxels(lig_pts, prot_pts, prot_radii):
    lo = lig_pts.min(0) - POCKET_RADIUS_A - 2
    hi = lig_pts.max(0) + POCKET_RADIUS_A + 2
    axes = [np.arange(lo[k], hi[k] + VOXEL_A, VOXEL_A) for k in range(3)]
    grid = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)

    near_lig = np.zeros(len(grid), dtype=bool)
    for c in lig_pts:
        near_lig |= ((grid - c) ** 2).sum(-1) <= POCKET_RADIUS_A ** 2

    in_prot = np.zeros(len(grid), dtype=bool)
    d_to_lig = np.sqrt(((prot_pts[:, None, :] - lig_pts[None, :, :]) ** 2).sum(-1)).min(1)
    close = d_to_lig <= POCKET_RADIUS_A + float(prot_radii.max())
    for c, rr in zip(prot_pts[close], prot_radii[close]):
        in_prot |= ((grid - c) ** 2).sum(-1) <= rr * rr

    return grid, near_lig & ~in_prot


def main():
    pts = sphere_points(N_SPHERE_POINTS)
    summary = {"phase": 14, "purpose": "pocket geometric descriptors (numpy)",
               "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "voxel_a": VOXEL_A, "probe_a": PROBE_A,
               "sphericity": "pi^(1/3)*(6V)^(2/3)/A via voxel boundary faces",
               "receptors": {}}
    pockets = load_json(os.path.join("paper2", "data", "structures",
                                     "pockets_defined.json"))["receptors"]

    for sym in all_symbols():
        rec = pockets[sym]
        chain, atoms, lig = structure_atoms(sym)
        tags, rows = parse_atom_site(os.path.join(STRUCT_DIR, f"{rec['pdb_id']}.cif"))

        all_heavy = [(a["auth_asym"], a["auth_seq"],
                      np.array([a["x"], a["y"], a["z"]]), a["element"])
                     for a in atom_rows(tags, rows) if a["element"].upper() != "H"]
        coords = np.stack([p[2] for p in all_heavy])
        radii = np.array([VDW.get(p[3].upper(), 1.7) + PROBE_A for p in all_heavy])

        atom_sasa = shrink_rupley(coords, radii, pts)
        res_sasa = {}
        for (ch, seq, _, _), s in zip(all_heavy, atom_sasa):
            if ch == chain:
                res_sasa[seq] = res_sasa.get(seq, 0.0) + s

        lig_pts = np.array([(l["x"], l["y"], l["z"]) for l in lig])
        centroid = lig_pts.mean(0)
        grid, pocket = pocket_voxels(
            lig_pts, coords,
            np.array([VDW.get(p[3].upper(), 1.7) for p in all_heavy]))
        volume_a3 = float(pocket.sum() * VOXEL_A ** 3)

        gdim = [len(np.unique(grid[:, k])) for k in range(3)]
        cube = pocket.reshape(gdim)
        faces = 0
        for axis in range(3):
            faces += int(np.abs(np.diff(cube.astype(np.int8), axis=axis)).sum())
        area_a2 = float(faces * VOXEL_A ** 2)
        sphericity = (float(np.pi ** (1 / 3) * (6 * volume_a3) ** (2 / 3) / area_a2)
                      if volume_a3 > 0 and area_a2 > 0 else 0.0)

        cas = ca_coords(sym)
        residues = pocket_residues(sym)
        ca_d = np.array([np.linalg.norm(cas[r["auth_seq_id"]] - centroid)
                         for r in residues])
        radius_a = float(ca_d.max())
        pocket_vox = grid[pocket]
        depth_a = float(np.linalg.norm(pocket_vox - centroid, axis=1).max())

        sasa_vec = np.array([res_sasa.get(r["auth_seq_id"], 0.0) for r in residues],
                            dtype=np.float32)

        out = os.path.join(FEATURE_DIR, f"{sym}_geometry.npz")
        np.savez_compressed(out, sasa_per_residue=sasa_vec,
                            uniprot_pos=np.array([r["uniprot_pos"] for r in residues]))
        summary["receptors"][sym] = {
            "volume_a3": round(volume_a3, 1),
            "surface_area_a2": round(area_a2, 1),
            "sphericity": round(sphericity, 3),
            "pocket_radius_ca_a": round(radius_a, 2),
            "pocket_depth_a": round(depth_a, 2),
            "mean_sasa_a2": round(float(sasa_vec.mean()), 2),
            "file": f"{sym}_geometry.npz",
        }
        print(f"{sym:8} vol={volume_a3:7.0f} A^3  area={area_a2:7.0f} A^2  "
              f"sph={sphericity:.3f}  r={radius_a:5.1f} A  depth={depth_a:5.1f} A  "
              f"meanSASA={sasa_vec.mean():5.1f} A^2", flush=True)
    save_json(summary, "paper2/data/features/phase14_summary.json")
    print("wrote", FEATURE_DIR)


if __name__ == "__main__":
    main()
