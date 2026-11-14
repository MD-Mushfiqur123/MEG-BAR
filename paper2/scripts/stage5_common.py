"""Shared Stage 5 helpers: AFDB-based pocket graphs and radius-sweep pockets.

Phase 27 (crystal-vs-AF): rebuilds each receptor's pocket graph from the
AlphaFold DB predicted model at the SAME UniProt pocket positions as the
crystal pocket (Phase 7/8), so the only change is the coordinate source.
pLDDT node features stay identical (Phase 6 AFDB pLDDT was already used in
the crystal graphs) - the comparison isolates geometry, not confidence.

Phase 28 (radius sweep): recomputes the pocket at 5.0/8.0 A around the SAME
chosen ligand copy in the SAME crystal structure, remaps residues to UniProt
positions, and rebuilds graphs. One deterministic pocket per (receptor,
radius); the anti-fishing rule forbids trying alternatives.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
STRUCT_DIR = os.path.join(REPO, 'paper2', 'data', 'structures')
FEATURE_DIR = os.path.join(REPO, 'paper2', 'data', 'features')

sys.path.insert(0, HERE)
from mmcif_lite import AA3TO1, atom_rows, het_rows, nw_align, parse_atom_site  # noqa: E402
from stage2_common import structure_atoms  # noqa: E402

POCKET_DIM = 128


def load_json(rel):
    with open(os.path.join(REPO, rel)) as f:
        return json.load(f)


def uniprot_sequence(sym):
    rec = load_json('data/real/proteins_expanded.json')[sym]
    return rec['sequence']


def parse_pdb_atoms(path):
    """Minimal stdlib PDB parser: heavy-atom records -> dicts with
    resnum, resname (1-letter), coords, element, bfactor."""
    out = []
    with open(path) as fh:
        for line in fh:
            if not line.startswith(('ATOM  ', 'HETATM')):
                continue
            altloc = line[16]
            if altloc not in (' ', 'A'):
                continue
            element = line[76:78].strip().upper()
            if not element:
                name = line[12:16].strip()
                element = ''.join(ch for ch in name if ch.isalpha())[:1].upper()
            if element in ('H', 'D'):
                continue
            try:
                xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
            except ValueError:
                continue
            out.append({
                'resnum': line[22:26].strip().lstrip('-'),
                'icode': line[26],
                'resname': AA3TO1.get(line[17:20].strip().upper(), 'X'),
                'xyz': xyz, 'element': element,
                'bfactor': float(line[60:66] or 0.0),
            })
    return out


def afdb_residue_coords(sym):
    """resnum(int) -> [resname1, [(x,y,z), ...]] from the AFDB model."""
    models = load_json('paper2/data/structures/afdb/afdb_models.json')['receptors']
    path = os.path.join(STRUCT_DIR, 'afdb', os.path.basename(models[sym]['file']))
    per = {}
    for a in parse_pdb_atoms(path):
        if a['resname'] == 'X' or a['icode'].strip():
            continue
        try:
            rn = int(a['resnum'])
        except ValueError:
            continue
        e = per.setdefault(rn, [a['resname'], []])
        e[1].append(a['xyz'])
    return per


def crystal_pocket_positions(sym):
    """UniProt 1-based pocket positions + residue letters (Phase 8 output)."""
    rec = load_json('paper2/data/structures/residue_mapping.json')['receptors'][sym]
    mapping = sorted(rec['mapping'], key=lambda r: r['uniprot_pos'])
    return [(int(m['uniprot_pos']), m['uniprot_residue']) for m in mapping]


def graph_from_coords(sym, residue_records):
    """residue_records: list of (uniprot_pos, resname1, [coords], plddt).
    Returns (NF, W, D) numpy arrays for one receptor, unpadded.
    Node features use the SAME PCA (mu/comps, float32, pocket-only stack)
    as stage3_common.load_pocket_contexts, so crystal-vs-AF differences
    come from geometry only."""
    ze = np.load(os.path.join(REPO, 'data', 'real',
                              'residue_embeddings_expanded.npz'), allow_pickle=True)
    full = ze['%s_residues' % sym]
    n = len(residue_records)
    nf = np.zeros((n, POCKET_DIM + 21), np.float32)
    dmat = np.full((n, n), 1e3, np.float32)
    wmat = np.zeros((n, n), np.float32)
    for i, (pos, _res, coords, plddt) in enumerate(residue_records):
        if not (1 <= pos <= full.shape[0]):
            raise ValueError('%s pocket pos %d outside ESM-2 matrix (%d rows)'
                             % (sym, pos, full.shape[0]))
        nf[i, :POCKET_DIM] = _pca_row(full[pos - 1])
        nf[i, POCKET_DIM + 'ACDEFGHIKLMNPQRSTVWY'.index(_res)] = 1.0
        nf[i, POCKET_DIM + 20] = plddt / 100.0
        for j in range(i + 1, n):
            d = _heavy_min(coords, residue_records[j][2])
            dmat[i, j] = dmat[j, i] = d
            if d <= 8.0:
                w = float(np.exp(-d / 3.0))
                wmat[i, j] = wmat[j, i] = w
    np.fill_diagonal(wmat, 1.0)
    W = wmat / wmat.sum(axis=1, keepdims=True)
    return nf, W, dmat


_PCA = {}


def _pca_mats():
    if 'comps' in _PCA:
        return _PCA
    mapping = load_json('paper2/data/structures/residue_mapping.json')['receptors']
    ze = np.load(os.path.join(REPO, 'data', 'real',
                              'residue_embeddings_expanded.npz'), allow_pickle=True)
    syms = sorted(mapping)
    # Exactly stage3_common.load_pocket_contexts: float32 stack of the pocket
    # residues' ESM-2 rows, mu/comps from SVD of the centred stack.
    stack = np.vstack([ze['%s_residues' % s][
        mapping[s]['esm2_residue_indices_0based']].astype(np.float32)
        for s in syms])
    mu = stack.mean(axis=0, keepdims=True)
    Xc = stack - mu
    _, _, Vt = np.linalg.svd(Xc, full_matrices=False)
    _PCA['mu'] = mu.astype(np.float32)
    _PCA['comps'] = Vt[:POCKET_DIM].astype(np.float32)
    var = float(((Xc @ _PCA['comps'].T) ** 2).sum() / (Xc ** 2).sum())
    _PCA['var'] = var
    return _PCA


def _pca_row(vec1280):
    pca = _pca_mats()
    return ((vec1280.astype(np.float32) - pca['mu'][0]) @ pca['comps'].T)


def _heavy_min(coords_a, coords_b):
    a = np.asarray(coords_a, np.float32)
    b = np.asarray(coords_b, np.float32)
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=-1)
    return float(d.min())


def crystal_plddt_by_pos(sym):
    """Phase 6 AFDB pLDDT keyed by UniProt position (used identically in the
    crystal graphs, so crystal-vs-AF isolates geometry only)."""
    models = load_json('paper2/data/structures/afdb/afdb_models.json')['receptors']
    return {int(k): float(v) for k, v in models[sym]['plddt'].items()}


def _pk_rows(sym, recs):
    """PCA-reduced ESM-2 rows (PK) for the given pocket residue records."""
    ze = np.load(os.path.join(REPO, 'data', 'real',
                              'residue_embeddings_expanded.npz'), allow_pickle=True)
    full = ze['%s_residues' % sym]
    return np.stack([_pca_row(full[pos - 1]) for pos, *_ in recs]).astype(np.float32)


def build_af_context(symbols):
    """Context dict in stage3_common's format, geometry from AFDB models at
    the crystal pocket's UniProt positions."""
    G, P = len(symbols), max(len(crystal_pocket_positions(s)) for s in symbols)
    PK = np.zeros((G, P, POCKET_DIM), np.float32)
    NF = np.zeros((G, P, POCKET_DIM + 21), np.float32)
    PM = np.zeros((G, P), np.float32)
    W = np.zeros((G, P, P), np.float32)
    D = np.full((G, P, P), 1e3, np.float32)
    meta = {}
    for i, sym in enumerate(symbols):
        coords = afdb_residue_coords(sym)
        plddt = crystal_plddt_by_pos(sym)
        recs = []
        missing = []
        for pos, res in crystal_pocket_positions(sym):
            if pos not in coords:
                missing.append(pos)
                continue
            recs.append((pos, res, coords[pos][1], plddt.get(pos, 50.0)))
        if not recs:
            raise SystemExit('%s: no crystal pocket residues found in AFDB model' % sym)
        nf, w, d = graph_from_coords(sym, recs)
        n = nf.shape[0]
        PK[i, :n] = _pk_rows(sym, recs)
        NF[i, :n] = nf
        PM[i, :n] = 1.0
        W[i, :n, :n] = w
        D[i, :n, :n] = d
        meta[sym] = {'n_pocket_residues': int(n), 'missing_in_afdb': missing,
                     'mean_plddt_in_pocket': round(float(np.mean(
                         [r[3] for r in recs])), 2)}
    return {'PK': _t(PK), 'PM': _t(PM), 'NF': _t(NF), 'W': _t(W), 'D': _t(D)}, meta


def _t(a):
    import torch
    return torch.from_numpy(a)


def build_sweep_context(symbols, radius):
    """Context dict with pockets recomputed at `radius` A around the chosen
    ligand copy in the same crystal structure (Phase 28)."""
    pockets = load_json('paper2/data/structures/pockets_defined.json')['receptors']
    mapping065 = load_json('paper2/data/structures/residue_mapping.json')['receptors']
    G = len(symbols)
    per = []
    pk_per = []
    meta = {}
    for sym in symbols:
        rec = pockets[sym]
        chain, atoms, lig = structure_atoms(sym)
        res_coords = {}
        for a in atoms:
            e = res_coords.setdefault(a['auth_seq'], [AA3TO1.get(a['comp_id'], 'X'), []])
            e[1].append((a['x'], a['y'], a['z']))
        hits = set()
        r2 = radius * radius
        for res_id, (_, coords) in res_coords.items():
            for c in coords:
                if any((c[0] - l['x']) ** 2 + (c[1] - l['y']) ** 2
                       + (c[2] - l['z']) ** 2 <= r2 for l in lig):
                    hits.add(res_id)
                    break
        auth_to_uniprot = {m['auth_seq_id']: int(m['uniprot_pos'])
                           for m in mapping065[sym]['mapping']}
        auth_to_uniprot.update(_align_new_auth(sym, chain, hits, res_coords,
                                               auth_to_uniprot))
        ze = np.load(os.path.join(REPO, 'data', 'real',
                                  'residue_embeddings_expanded.npz'), allow_pickle=True)
        full = ze['%s_residues' % sym]
        plddt = crystal_plddt_by_pos(sym)
        recs = []
        for res_id in sorted(hits, key=lambda x: auth_to_uniprot.get(x, 10 ** 6)):
            pos = auth_to_uniprot.get(res_id)
            if pos is None or not (1 <= pos <= full.shape[0]):
                continue
            res1 = res_coords[res_id][0]
            if res1 == 'X':
                continue
            recs.append((pos, res1, res_coords[res_id][1], plddt.get(pos, 50.0)))
        seen, uniq = set(), []
        for r in recs:
            if r[0] not in seen:
                seen.add(r[0])
                uniq.append(r)
        uniq.sort(key=lambda r: r[0])
        if not uniq:
            raise SystemExit('%s: empty %s A pocket' % (sym, radius))
        nf, w, d = graph_from_coords(sym, uniq)
        per.append((nf, w, d))
        pk_per.append(_pk_rows(sym, uniq))
        meta[sym] = {'n_pocket_residues': int(nf.shape[0]), 'radius_a': radius,
                     'ligand': rec['ligand']['comp_id']}
    P = max(nf.shape[0] for nf, _, _ in per)
    PK = np.zeros((G, P, POCKET_DIM), np.float32)
    NF = np.zeros((G, P, POCKET_DIM + 21), np.float32)
    PM = np.zeros((G, P), np.float32)
    W = np.zeros((G, P, P), np.float32)
    D = np.full((G, P, P), 1e3, np.float32)
    for i, (nf, w, d) in enumerate(per):
        n = nf.shape[0]
        PK[i, :n] = pk_per[i]
        NF[i, :n] = nf
        PM[i, :n] = 1.0
        W[i, :n, :n] = w
        D[i, :n, :n] = d
    return {'PK': _t(PK), 'PM': _t(PM), 'NF': _t(NF), 'W': _t(W), 'D': _t(D)}, meta


def _align_new_auth(sym, chain, hits, res_coords, known):
    """auth_seq_id -> UniProt pos for pocket residues not covered by the 6.5 A
    mapping, via NW alignment of the receptor chain (same method as Phase 8)."""
    uniprot_seq = uniprot_sequence(sym)
    seq, auth_ids, seen = [], [], set()
    atoms = None
    rec = load_json('paper2/data/structures/pockets_defined.json')['receptors'][sym]
    tags, rows = parse_atom_site(os.path.join(STRUCT_DIR, '%s.cif' % rec['pdb_id']))
    atoms = [a for a in atom_rows(tags, rows)
             if a['auth_asym'] == chain and a['element'].upper() != 'H']
    for a in atoms:
        if a['auth_seq'] in seen:
            continue
        aa = AA3TO1.get(a['comp_id'].upper())
        if aa is None:
            continue
        seen.add(a['auth_seq'])
        seq.append(aa)
        auth_ids.append(a['auth_seq'])
    pairs = nw_align(''.join(seq), uniprot_seq)
    out = {}
    for i, j in pairs:
        if auth_ids[i] in hits and auth_ids[i] not in known:
            out[auth_ids[i]] = j + 1
    return out
