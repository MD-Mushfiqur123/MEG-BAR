#!/usr/bin/env python3
"""13_expanded_eval.py — Phase 3: rerun the Phase-1 protocols on the expanded set.

Reuses the tested training/eval code from 08_robust_eval.py (imported as a
module) and applies it to the eleven-receptor evidence base:

  E3  scaffold-disjoint within-receptor (identical protocol to 08)
  E5  temporal split: train on records published before 2015,
      test on records published 2015+ (document years resolved live from
      ChEMBL by 11_expand_receptors.py); records without a year are excluded
      and the exclusion is reported.

  Architectures: shared MLP, cross-attention conditioning, wrong-pocket
  control, Ridge-on-fingerprint baseline; five seeds; paired Wilcoxon.

Outputs (data/real/):
  ligand_fp_cache_expanded.npz
  expanded_results.json
  expanded_report.md
"""
import importlib.util
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
from rdkit.Chem.Scaffolds import MurckoScaffold

RDLogger.DisableLog('rdApp.*')

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))

FP_BITS, FP_RADIUS = 2048, 2
TEMPORAL_CUTOFF = 2015


def load_08():
    spec = importlib.util.spec_from_file_location(
        'robust_eval', os.path.join(HERE, '08_robust_eval.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules['robust_eval'] = mod
    spec.loader.exec_module(mod)
    return mod


def fingerprints(smiles):
    cache_path = os.path.join(DATA, 'ligand_fp_cache_expanded.npz')
    if os.path.isfile(cache_path):
        z = np.load(cache_path, allow_pickle=True)
        if len(z['smiles']) == len(smiles) and bool((z['smiles'] == np.array(smiles)).all()):
            print('[fp] cache hit (%d molecules)' % len(smiles), flush=True)
            return z['fp'].astype(np.float32), z['scaffold']
    print('[fp] computing %d Morgan fingerprints...' % len(smiles), flush=True)
    fp = np.zeros((len(smiles), FP_BITS), np.float32)
    scaf = []
    for i, s in enumerate(smiles):
        mol = Chem.MolFromSmiles(s)
        if mol is not None:
            bv = AllChem.GetMorganFingerprintAsBitVect(mol, FP_RADIUS, nBits=FP_BITS)
            AllChem.DataStructs.ConvertToNumpyArray(bv, fp[i])
        try:
            sc = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False) if mol else ''
        except Exception:                     # noqa: BLE001
            sc = ''
        scaf.append(sc)
        if (i + 1) % 5000 == 0:
            print('    %d / %d' % (i + 1, len(smiles)), flush=True)
    np.savez_compressed(cache_path, smiles=np.array(smiles), fp=fp, scaffold=np.array(scaf))
    return fp, np.array(scaf)


def load_pockets_expanded(genes):
    z = np.load(os.path.join(DATA, 'residue_embeddings_expanded.npz'), allow_pickle=True)
    with open(os.path.join(DATA, 'pockets_expanded.json'), encoding='utf-8') as fh:
        pk = json.load(fh)['receptors']
    mod = sys.modules['robust_eval']
    raw = {}
    for g in genes:
        full = z['%s_residues' % g]
        idx = [i - 1 for i in pk[g]['pocket_residues_1based']]
        idx = [i for i in idx if 0 <= i < len(full)]
        raw[g] = full[idx].astype(np.float32)
    stack = np.vstack([raw[g] for g in genes])
    mu = stack.mean(axis=0, keepdims=True)
    Xc = stack - mu
    _, _, Vt = np.linalg.svd(Xc, full_matrices=False)
    comps = Vt[:mod.POCKET_DIM]
    var = float(((Xc @ comps.T) ** 2).sum() / (Xc ** 2).sum())
    P = max(m.shape[0] for m in raw.values())
    pocket = np.zeros((len(genes), P, mod.POCKET_DIM), np.float32)
    mask = np.zeros((len(genes), P), np.float32)
    for i, g in enumerate(genes):
        m = raw[g]
        pocket[i, :m.shape[0]] = ((m - mu) @ comps.T).astype(np.float32)
        mask[i, :m.shape[0]] = 1.0
    n = len(genes)
    wrong = np.stack([pocket[(i + 1) % n] for i in range(n)])
    wrong_mask = np.stack([mask[(i + 1) % n] for i in range(n)])
    print('[ctx] pocket %s PCA(1280->%d) var=%.3f; wrong-pocket control built'
          % (pocket.shape, mod.POCKET_DIM, var), flush=True)
    return pocket, mask, wrong, wrong_mask, {'variance_explained': round(var, 6),
                                             'pocket_sizes': {g: int(raw[g].shape[0]) for g in genes}}


def temporal_split(idx, years, doc_ids, seed=42):
    """Train pre-cutoff, test >= cutoff; val carved from train. Returns None if too small."""
    tr_pool, te = [], []
    for i in idx:
        y = years.get(doc_ids[i])
        if y is None:
            continue
        (te if y >= TEMPORAL_CUTOFF else tr_pool).append(i)
    te = np.array(te, dtype=int)
    tr_pool = np.array(tr_pool, dtype=int)
    if len(te) < 50 or len(tr_pool) < 400:
        return None
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(tr_pool))
    n_va = int(0.15 * len(tr_pool))
    va, tr = tr_pool[perm[:n_va]], tr_pool[perm[n_va:]]
    return tr, va, te


def main():
    t_start = time.time()
    mod = load_08()
    print('[*] loaded 08_robust_eval module (archs=%s, seeds=%s, min_train=%d)'
          % (mod.ARCHS, mod.SEEDS, mod.MIN_TRAIN), flush=True)

    df = pd.read_csv(os.path.join(DATA, 'raw_activities_expanded.csv'))
    df['pchembl_value'] = pd.to_numeric(df['pchembl_value'], errors='coerce')
    df = df.dropna(subset=['pchembl_value', 'smiles'])
    df = (df.groupby(['gene', 'molecule_chembl_id'], as_index=False)
            .agg(pchembl=('pchembl_value', 'median'), smiles=('smiles', 'first'))).reset_index(drop=True)
    with open(os.path.join(DATA, 'document_years.json'), encoding='utf-8') as fh:
        years = json.load(fh)
    doc_ids = pd.read_csv(os.path.join(DATA, 'raw_activities_expanded.csv'),
                          usecols=['molecule_chembl_id', 'document_chembl_id'])
    doc_map = (doc_ids.dropna().groupby('molecule_chembl_id')['document_chembl_id'].first().to_dict())
    DOC = df['molecule_chembl_id'].map(lambda m: doc_map.get(m, '')).values

    uniq_smiles = df.smiles.drop_duplicates().tolist()
    FP, SCAFF = fingerprints(uniq_smiles)
    smi2i = {s: i for i, s in enumerate(uniq_smiles)}
    FPI = np.array([smi2i[s] for s in df.smiles])
    FP = FP[FPI]
    SCAFF = SCAFF[FPI]
    y = df.pchembl.values.astype(np.float32)
    genes = sorted(df.gene.unique())
    print('[data] n=%d pairs, genes=%s' % (len(df), genes), flush=True)

    pocket, mask, wrong, wrong_mask, pca = load_pockets_expanded(genes)
    g2i = {g: i for i, g in enumerate(genes)}
    PIDX = np.array([g2i[g] for g in df.gene])
    PK_T, PM_T = torch.from_numpy(pocket), torch.from_numpy(mask)
    WK_T, WM_T = torch.from_numpy(wrong), torch.from_numpy(wrong_mask)

    out_path = os.path.join(DATA, 'expanded_results.json')
    store = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding='utf-8') as fh:
                store = json.load(fh)
            store = {k: v for k, v in store.items() if not k.startswith('_')}
        except Exception:                     # noqa: BLE001
            store = {}

    def flush():
        clean = {k: v for k, v in store.items() if not k.startswith('_')}
        clean.update({
            'purpose': 'Phase-3 expanded measured evaluation (11 receptors, scaffold + temporal splits)',
            'seeds': mod.SEEDS, 'archs': mod.ARCHS, 'min_train': mod.MIN_TRAIN,
            'temporal_cutoff': TEMPORAL_CUTOFF,
            'optimizer': {'name': 'AdamW', 'lr_peak': mod.LR_PEAK, 'weight_decay': mod.WEIGHT_DECAY,
                          'clip_norm': mod.CLIP, 'schedule': 'cosine with 5% warmup',
                          'dropout': mod.DROPOUT, 'batch': mod.BATCH,
                          'max_epochs': mod.MAX_EPOCHS, 'patience': mod.PATIENCE},
            'pocket_pca': pca,
            'records_per_gene': df.gene.value_counts().to_dict(),
        })
        with open(out_path, 'w', encoding='utf-8') as fh:
            json.dump(clean, fh, indent=2)

    store['_flush'] = flush
    flush()

    print('\n=== E3: scaffold-disjoint within-receptor (11 receptors) ===', flush=True)
    for g in genes:
        if mod.block_complete(store.get('E3|' + g)):
            print('  %-8s [resume] complete' % g, flush=True)
            continue
        idx = df.index[df.gene == g].values
        sp = mod.scaffold_split(SCAFF[idx])
        if sp is None:
            print('  %-8s skipped (too few scaffolds)' % g, flush=True)
            continue
        tr, va, te = idx[sp[0]], idx[sp[1]], idx[sp[2]]
        print('  %-8s n_tr=%d n_va=%d n_te=%d' % (g, len(tr), len(va), len(te)), flush=True)
        mod.run_block('E3|' + g, tr, va, te, FP, PK_T, PM_T, PIDX, y, store, WK_T, WM_T)

    print('\n=== E5: temporal split (train < %d, test >= %d) ===' % (TEMPORAL_CUTOFF, TEMPORAL_CUTOFF), flush=True)
    n_no_year = 0
    for g in genes:
        if mod.block_complete(store.get('E5|' + g)):
            print('  %-8s [resume] complete' % g, flush=True)
            continue
        idx = df.index[df.gene == g].values
        sp = temporal_split(idx, years, DOC)
        if sp is None:
            print('  %-8s skipped (insufficient dated records)', flush=True)
            continue
        tr, va, te = sp
        n_no_year += int(sum(1 for i in idx if years.get(DOC[i]) is None))
        print('  %-8s n_tr=%d n_va=%d n_te=%d' % (g, len(tr), len(va), len(te)), flush=True)
        mod.run_block('E5|' + g, tr, va, te, FP, PK_T, PM_T, PIDX, y, store, WK_T, WM_T)

    store.pop('_flush', None)
    flush()

    # ------------------------------------------------------------- markdown
    L = ['# MEG-BAR — Phase 3 expanded measured evaluation', '',
         'Eleven receptors (four original + HTR1A, DRD3, ADRA2A, ADRB2, SERT, DAT, HRH1).',
         'Architectures and protocol identical to 08_robust_eval.py; temporal split trains on',
         'pre-%d records and tests on %d+ records (document years resolved from ChEMBL).' % (TEMPORAL_CUTOFF, TEMPORAL_CUTOFF), '']

    def table(prefix, title):
        L.extend(['## ' + title, '',
                  '| Split | Arch | mean r | sd | 95% CI | mean rho |',
                  '|---|---|---|---|---|---|'])
        for key in sorted(k for k in store if k.startswith(prefix)):
            blk = store[key]
            split = key.split('|', 1)[1]
            for arch in ['ridge', 'shared', 'crossattn', 'crossattn_wrongpocket']:
                rec = blk.get(arch)
                if not rec:
                    continue
                if 'skipped' in rec:
                    L.append('| %s | %s | skipped | - | %s | - |' % (split, arch, rec['skipped']))
                    continue
                if 'mean_r' in rec:
                    L.append('| %s | %s | %.3f | %.3f | [%.3f, %.3f] | %.3f |'
                             % (split, arch, rec['mean_r'], rec['sd_r'],
                                rec['bootstrap_ci'][0], rec['bootstrap_ci'][1],
                                np.mean([r['spearman_rho'] for r in rec['seeds']])))
                else:
                    L.append('| %s | %s | %.3f | - | [%.3f, %.3f] | %.3f |'
                             % (split, arch, rec['pearson_r'],
                                rec['bootstrap_ci'][0], rec['bootstrap_ci'][1], rec['spearman_rho']))
            w = blk.get('wilcoxon_crossattn_vs_shared')
            if w and 'pvalue' in w:
                L.append('| %s | _Wilcoxon crossattn vs shared_ | p = %.4f | | mean diff %+.3f | |'
                         % (split, w['pvalue'], w['mean_diff']))
        L.append('')

    table('E3|', 'E3 — scaffold-disjoint within-receptor')
    table('E5|', 'E5 — temporal split (train pre-%d, test %d+)' % (TEMPORAL_CUTOFF, TEMPORAL_CUTOFF))
    L.append('Records without a document year (excluded from E5): %d' % n_no_year)
    L.append('Wall clock: %.1f s' % (time.time() - t_start))
    with open(os.path.join(DATA, 'expanded_report.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')

    print('\n[OK] wrote expanded_results.json + expanded_report.md in %.1fs' % (time.time() - t_start), flush=True)


if __name__ == '__main__':
    sys.exit(main())
