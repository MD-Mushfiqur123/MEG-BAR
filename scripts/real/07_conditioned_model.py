#!/usr/bin/env python3
"""07_conditioned_model.py — does receptor conditioning actually help? Measured.

Three architectures, identical data, identical splits, identical training budget:

  A. shared      : MLP on the Morgan fingerprint only.           (baseline)
  B. const_ctx   : MLP on fingerprint + mean-pooled ESM-2 vector (previous design;
                   the receptor vector is constant within a receptor)
  C. crossattn   : ligand tokens cross-attend to REAL annotated pocket-residue
                   embeddings, so the receptor context is applied differently for
                   every ligand.  (the fix)

C is the architecture that addresses the diagnosed failure mode: a receptor vector
that never varies cannot condition anything, whereas attention weights depend on
the ligand.

Evaluated on:
  E3  scaffold-disjoint within-receptor splits  (Bemis-Murcko, overlap verified 0)
  E4  leave-one-receptor-out                    (target receptor unseen in training,
                                                 but its pocket annotation is available)

All numbers are measured. Outputs (data/real/):
  conditioned_results.json
  conditioned_report.md
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
from rdkit.Chem.Scaffolds import MurckoScaffold
from scipy import stats

RDLogger.DisableLog('rdApp.*')
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))
OUT = DATA

SEED = 42
FP_BITS, FP_RADIUS = 2048, 2
N_TOKENS = 32                 # fingerprint chunked into 32 ligand tokens
TOKEN_DIM = FP_BITS // N_TOKENS
D_MODEL = 128
POCKET_DIM = 128      # PCA-reduced pocket residue dimension
N_HEADS = 4
HIDDEN = 256
DROPOUT = 0.2
LR, BATCH, MAX_EPOCHS, PATIENCE, BOOT = 1e-3, 512, 90, 8, 1000

torch.manual_seed(SEED)
np.random.seed(SEED)
torch.set_num_threads(os.cpu_count() or 4)


# ------------------------------------------------------------------ features
def load_ligands():
    cache = os.path.join(DATA, 'ligand_fp_cache.npz')
    df = pd.read_csv(os.path.join(DATA, 'raw_activities.csv'))
    df['pchembl_value'] = pd.to_numeric(df['pchembl_value'], errors='coerce')
    df = df.dropna(subset=['pchembl_value', 'smiles'])
    df = (df.groupby(['gene', 'molecule_chembl_id'], as_index=False)
            .agg(pchembl=('pchembl_value', 'median'), smiles=('smiles', 'first')))
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        if len(z['smiles']) == len(df) and bool((z['smiles'] == df.smiles.values).all()):
            print('[fp] loaded cache %s' % cache, flush=True)
            return df, z['fp'].astype(np.float32), z['scaffold']
    fps, scaff = [], []
    for smi in df.smiles:
        m = Chem.MolFromSmiles(smi)
        fp = AllChem.GetMorganFingerprintAsBitVect(m, FP_RADIUS, nBits=FP_BITS)
        a = np.zeros((FP_BITS,), np.float32)
        AllChem.DataStructs.ConvertToNumpyArray(fp, a)
        fps.append(a)
        scaff.append(MurckoScaffold.MurckoScaffoldSmiles(mol=m, includeChirality=False) or smi)
    fp = np.vstack(fps).astype(np.float32)
    sc = np.array(scaff)
    np.savez_compressed(cache, fp=fp, scaffold=sc, smiles=df.smiles.values)
    print('[fp] computed and cached %d fingerprints' % len(fp), flush=True)
    return df, fp, sc


def load_contexts(genes):
    """Per gene: mean-pooled vector (D,), PCA-reduced pocket matrix (P, POCKET_DIM),
    and a validity mask. PCA is fitted on the pocket residues themselves so the
    reduction is data-derived, not arbitrary."""
    z = np.load(os.path.join(DATA, 'residue_embeddings.npz'), allow_pickle=True)
    with open(os.path.join(DATA, 'pockets.json'), encoding='utf-8') as fh:
        pockets = json.load(fh)['receptors']

    const, raw = {}, {}
    for g in genes:
        full = z['%s_residues' % g]
        const[g] = full.mean(axis=0).astype(np.float32)
        idx = [i - 1 for i in pockets[g]['pocket_residues_1based']]
        idx = [i for i in idx if 0 <= i < len(full)]
        raw[g] = full[idx].astype(np.float32)

    # PCA over all pocket residues pooled across receptors.
    stack = np.vstack([raw[g] for g in genes])
    mu = stack.mean(axis=0, keepdims=True)
    Xc = stack - mu
    # economical SVD: samples x features, keep POCKET_DIM components
    _, _, Vt = np.linalg.svd(Xc, full_matrices=False)
    comps = Vt[:POCKET_DIM]                              # (POCKET_DIM, 1280)
    var_explained = float(((Xc @ comps.T) ** 2).sum() / (Xc ** 2).sum())

    P = max(m.shape[0] for m in raw.values())
    pocket = np.zeros((len(genes), P, POCKET_DIM), np.float32)
    mask = np.zeros((len(genes), P), np.float32)
    for i, g in enumerate(genes):
        m = raw[g]
        reduced = (m - mu) @ comps.T
        pocket[i, :m.shape[0]] = reduced.astype(np.float32)
        mask[i, :m.shape[0]] = 1.0
    print('[ctx] pocket tensor %s  PCA(%d->%d) var_explained=%.3f  pocket_sizes=%s'
          % (pocket.shape, stack.shape[1], POCKET_DIM, var_explained,
             {g: raw[g].shape[0] for g in genes}), flush=True)
    manifest = {
        'pca_components': POCKET_DIM, 'input_dim': int(stack.shape[1]),
        'n_pocket_residues_total': int(stack.shape[0]),
        'variance_explained': round(var_explained, 6),
        'pocket_sizes': {g: int(raw[g].shape[0]) for g in genes},
    }
    return const, pocket, mask, {g: raw[g].shape[0] for g in genes}, manifest


# -------------------------------------------------------------------- models
class SharedMLP(nn.Module):
    def __init__(self, d_in):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, HIDDEN), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN // 2, 1))

    def forward(self, fp, const=None, pocket=None, pmask=None):
        return self.net(fp).squeeze(-1)


class ConstCtxMLP(nn.Module):
    """Previous design: fingerprint + a constant per-receptor ESM-2 vector."""

    def __init__(self, d_in, d_ctx):
        super().__init__()
        self.ctx = nn.Sequential(nn.Linear(d_ctx, D_MODEL), nn.GELU())
        self.net = nn.Sequential(
            nn.Linear(d_in + D_MODEL, HIDDEN), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN // 2, 1))

    def forward(self, fp, const=None, pocket=None, pmask=None):
        c = self.ctx(const)
        return self.net(torch.cat([fp, c], dim=1)).squeeze(-1)


class CrossAttentionConditioned(nn.Module):
    """Ligand tokens cross-attend to real pocket-residue embeddings."""

    def __init__(self, d_in, d_res, d_model=D_MODEL, n_heads=N_HEADS):
        super().__init__()
        self.tok = nn.Sequential(nn.Linear(TOKEN_DIM, d_model), nn.GELU())
        self.proj_kv = nn.Linear(d_res, d_model)   # d_res == POCKET_DIM after PCA
        self.attn = nn.MultiheadAttention(d_model, n_heads, dropout=DROPOUT, batch_first=True)
        self.ligand_global = nn.Sequential(nn.Linear(d_in, d_model), nn.GELU())
        self.head = nn.Sequential(
            nn.Linear(2 * d_model, HIDDEN), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN // 2, 1))

    def forward(self, fp, const=None, pocket=None, pmask=None):
        b = fp.shape[0]
        q = self.tok(fp.view(b, N_TOKENS, TOKEN_DIM))          # (B, T, d)
        kv = self.proj_kv(pocket)                              # (B, P, d)
        kpm = (pmask < 0.5)                                    # True = ignore
        ctx, _ = self.attn(q, kv, kv, key_padding_mask=kpm, need_weights=False)
        ctx = ctx.mean(dim=1)                                  # (B, d)
        g = self.ligand_global(fp)
        return self.head(torch.cat([ctx, g], dim=1)).squeeze(-1)


# --------------------------------------------------------------- utilities
def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {'pearson_r': float(stats.pearsonr(y, p)[0]),
            'spearman_rho': float(stats.spearmanr(y, p)[0]),
            'rmse': float(np.sqrt(np.mean((y - p) ** 2))),
            'mae': float(np.mean(np.abs(y - p))), 'n': int(len(y))}


def bootstrap(y, p, n_boot=BOOT):
    rng = np.random.default_rng(SEED)
    n, rs = len(y), []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        if np.std(np.asarray(p)[i]) == 0:
            continue
        rs.append(stats.pearsonr(np.asarray(y)[i], np.asarray(p)[i])[0])
    a = np.array(rs)
    return {'mean': float(a.mean()), 'sd': float(a.std()),
            'ci95': [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]}


def train_eval(model, tr, va, te, FP, CONST, POCKET_T, PMASK_T, PIDX, y, verbose=False):
    """Train with memory-safe on-the-fly batching.

    POCKET_T: torch (G, P, POCKET_DIM); PMASK_T: torch (G, P).
    Only the current batch is ever gathered, so memory is O(batch*P*D).
    """
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    lossf = nn.SmoothL1Loss(beta=0.5)
    y_t = torch.tensor(y, dtype=torch.float32)
    pid = torch.as_tensor(PIDX, dtype=torch.long)

    def batch(idx):
        ii = torch.as_tensor(idx, dtype=torch.long)
        g = pid[ii]
        return (torch.from_numpy(FP[idx]), torch.from_numpy(CONST[idx]),
                POCKET_T[g], PMASK_T[g], y_t[ii])

    best, state, bad, ep = 1e9, None, 0, 0
    n = len(tr)
    for ep in range(MAX_EPOCHS):
        model.train()
        perm = np.random.default_rng(SEED + ep).permutation(n)
        for b in range(0, n, BATCH):
            ii = tr[perm[b:b + BATCH]]
            f, c, pk, pm, t = batch(ii)
            opt.zero_grad()
            loss = lossf(model(f, c, pk, pm), t)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            vf, vc, vp, vm, vt = batch(va)
            vl = float(lossf(model(vf, vc, vp, vm), vt))
        if vl < best - 1e-5:
            best, bad = vl, 0
            state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    if state:
        model.load_state_dict(state)
    model.eval()
    preds = []
    with torch.no_grad():
        for b in range(0, len(te), 2048):
            f, c, pk, pm, _ = batch(te[b:b + 2048])
            preds.append(model(f, c, pk, pm).numpy())
    return np.concatenate(preds), ep + 1


def scaffold_groups(scaffolds):
    g = {}
    for i, s in enumerate(scaffolds):
        g.setdefault(s, []).append(i)
    return g


def make_scaffold_split(scaff, frac_test=0.2, frac_val=0.15, min_per=30):
    n = len(scaff)
    groups = scaffold_groups(scaff)
    order = sorted(groups, key=lambda k: -len(groups[k]))
    n_test, n_val = int(frac_test * n), int(frac_val * n)
    test, val = [], []
    for k in order:
        if len(test) + len(groups[k]) <= n_test:
            test.extend(groups[k])
        elif len(val) + len(groups[k]) <= n_val:
            val.extend(groups[k])
    used = set(test) | set(val)
    train = [i for i in range(n) if i not in used]
    if min(len(train), len(test), len(val)) < min_per:
        return None
    return np.array(train), np.array(val), np.array(test)


ARCHS = ['shared', 'const_ctx', 'crossattn']


def build(arch, d_fp, d_const, d_pocket):
    if arch == 'shared':
        return SharedMLP(d_fp)
    if arch == 'const_ctx':
        return ConstCtxMLP(d_fp, d_const)
    return CrossAttentionConditioned(d_fp, d_pocket)


def main():
    t0 = time.time()
    df, FP, SCAFF = load_ligands()
    genes = sorted(df.gene.unique())
    y = df.pchembl.values.astype(np.float32)
    CONST_vec, POCKET_NP, PMASK_NP, pocket_sizes, pca_meta = load_contexts(genes)
    gene_to_ctx = {g: i for i, g in enumerate(genes)}
    CONST = np.vstack([CONST_vec[g] for g in df.gene]).astype(np.float32)
    PIDX = np.array([gene_to_ctx[g] for g in df.gene])
    POCKET_T = torch.from_numpy(POCKET_NP)
    PMASK_T = torch.from_numpy(PMASK_NP)

    print('[data] n=%d genes=%s pocket_sizes=%s' % (len(df), genes, pocket_sizes), flush=True)

    out_path = os.path.join(OUT, 'conditioned_results.json')
    res = None
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding='utf-8') as fh:
                prev = json.load(fh)
            if prev.get('E3_scaffold_within_receptor'):
                res = prev
                print('[resume] reusing E3 from %s (%d receptors)'
                      % (out_path, len(prev['E3_scaffold_within_receptor'])), flush=True)
        except Exception:                      # noqa: BLE001
            res = None
    if res is None:
        res = {'E3_scaffold_within_receptor': {}, 'E4_leave_one_receptor_out': {}}
    res.update({
        'purpose': 'REAL measured: does receptor conditioning help? (no simulation)',
        'seed': SEED,
        'n_molecules': int(len(df)),
        'pocket_sizes': pocket_sizes,
        'pocket_pca': pca_meta,
        'architectures': ARCHS,
        'hyperparameters': {'n_tokens': N_TOKENS, 'token_dim': TOKEN_DIM, 'd_model': D_MODEL,
                            'pocket_dim': POCKET_DIM, 'n_heads': N_HEADS, 'hidden': HIDDEN,
                            'lr': LR, 'batch': BATCH, 'max_epochs': MAX_EPOCHS,
                            'patience': PATIENCE, 'bootstrap': BOOT},
    })
    res.setdefault('E4_leave_one_receptor_out', {})

    def flush():
        with open(out_path, 'w', encoding='utf-8') as fh:
            json.dump(res, fh, indent=2)

    d_pocket = POCKET_NP.shape[2]
    d_const = CONST.shape[1]

    if not res['E3_scaffold_within_receptor']:
        print('\n=== E3: scaffold-disjoint within-receptor ===', flush=True)
        for g in genes:
            idx = df.index[df.gene == g].values
            split = make_scaffold_split(SCAFF[idx], min_per=30)
            if split is None:
                print('  %-8s skipped (too few scaffolds)' % g, flush=True)
                continue
            tr, va, te = split
            tr_g, va_g, te_g = idx[tr], idx[va], idx[te]
            block = {}
            for arch in ARCHS:
                torch.manual_seed(SEED)
                m = build(arch, FP_BITS, d_const, d_pocket)
                pred, eps = train_eval(m, tr_g, va_g, te_g, FP, CONST, POCKET_T, PMASK_T, PIDX, y)
                met = metrics(y[te_g], pred)
                met['bootstrap'] = bootstrap(y[te_g], pred)
                met['epochs'] = int(eps)
                met['n_train'], met['n_test'] = int(len(tr_g)), int(len(te_g))
                met['test_scaffold_overlap'] = int(len(set(SCAFF[te_g]) & set(SCAFF[tr_g])))
                block[arch] = met
            res['E3_scaffold_within_receptor'][g] = block
            flush()
            print('  %-8s n_tr=%-5d n_te=%-4d' % (g, len(tr_g), len(te_g)), flush=True)
            for arch in ARCHS:
                m = block[arch]
                ci = m['bootstrap']['ci95']
                print('      %-11s r=%.3f [%.3f,%.3f]  rho=%.3f  RMSE=%.3f'
                      % (arch, m['pearson_r'], ci[0], ci[1], m['spearman_rho'], m['rmse']), flush=True)
    else:
        print('[skip] E3 already complete', flush=True)

    print('\n=== E4: leave-one-receptor-out ===', flush=True)
    for held in genes:
        if held in res.get('E4_leave_one_receptor_out', {}):
            print('  %-8s [resume] already complete' % held, flush=True)
            continue
        te = df.index[df.gene == held].values
        pool = df.index[df.gene != held].values
        if len(te) < 40 or len(pool) < 300:
            print('  %-8s skipped' % held, flush=True)
            continue
        rng = np.random.default_rng(SEED)
        perm = rng.permutation(len(pool))
        n_va = int(0.15 * len(pool))
        va, tr = pool[perm[:n_va]], pool[perm[n_va:]]
        block = {}
        for arch in ARCHS:
            torch.manual_seed(SEED)
            m = build(arch, FP_BITS, d_const, d_pocket)
            pred, eps = train_eval(m, tr, va, te, FP, CONST, POCKET_T, PMASK_T, PIDX, y)
            met = metrics(y[te], pred)
            met['bootstrap'] = bootstrap(y[te], pred)
            met['epochs'] = int(eps)
            met['n_train'], met['n_test'] = int(len(tr)), int(len(te))
            block[arch] = met
        res['E4_leave_one_receptor_out'][held] = block
        flush()
        print('  held-out %-8s n_tr=%-5d n_te=%-4d' % (held, len(tr), len(te)), flush=True)
        for arch in ARCHS:
            m = block[arch]
            ci = m['bootstrap']['ci95']
            print('      %-11s r=%+.3f [%+.3f,%+.3f]  rho=%+.3f  RMSE=%.3f'
                  % (arch, m['pearson_r'], ci[0], ci[1], m['spearman_rho'], m['rmse']), flush=True)

    res['wall_clock_seconds'] = round(time.time() - t0, 1)
    res['completed_utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    flush()

    L = ['# MEG-BAR — receptor conditioning: measured comparison', '',
         'Architectures: **shared** (fingerprint only), **const_ctx** (fingerprint +',
         'mean-pooled ESM-2 receptor vector), **crossattn** (ligand tokens cross-attend',
         'to real UniProt-annotated pocket residues, PCA-reduced to %d dims).' % POCKET_DIM,
         'Pocket PCA variance explained: %.3f' % pca_meta['variance_explained'], '',
         '## E3 — scaffold-disjoint within-receptor', '',
         '| Receptor | Arch | Pearson r | 95% CI | Spearman | RMSE |',
         '|---|---|---|---|---|---|']
    for g, b in res['E3_scaffold_within_receptor'].items():
        for arch in ARCHS:
            m = b[arch]
            ci = m['bootstrap']['ci95']
            L.append('| %s | %s | %.3f | [%.3f, %.3f] | %.3f | %.3f |'
                     % (g, arch, m['pearson_r'], ci[0], ci[1], m['spearman_rho'], m['rmse']))
    L += ['', '## E4 — leave-one-receptor-out', '',
          '| Held out | Arch | Pearson r | 95% CI | Spearman | RMSE |',
          '|---|---|---|---|---|---|']
    for g, b in res['E4_leave_one_receptor_out'].items():
        for arch in ARCHS:
            m = b[arch]
            ci = m['bootstrap']['ci95']
            L.append('| %s | %s | %.3f | [%.3f, %.3f] | %.3f | %.3f |'
                     % (g, arch, m['pearson_r'], ci[0], ci[1], m['spearman_rho'], m['rmse']))
    L += ['', 'Wall clock: %.1f s' % res['wall_clock_seconds']]
    with open(os.path.join(OUT, 'conditioned_report.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')

    print('\n[OK] wrote conditioned_results.json + conditioned_report.md in %.1fs'
          % res['wall_clock_seconds'], flush=True)


if __name__ == '__main__':
    sys.exit(main())
