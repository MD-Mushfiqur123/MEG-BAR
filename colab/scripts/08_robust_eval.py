#!/usr/bin/env python3
"""08_robust_eval.py — Phase 1: make every measured number statistically sound.

Fixes applied relative to 07_conditioned_model.py:
  * AdamW with weight_decay=0.01 (was plain Adam, no decay)  -> the GABA-A run diverged
  * gradient clipping at norm 1.0
  * cosine LR schedule with 5% warmup, peak 5e-4 (was constant 1e-3)
  * higher dropout when the target has little data
  * MIN_TRAIN guard: the cross-attention arm is skipped and reported as skipped,
    never silently substituted
  * five seeds per configuration, reporting mean +/- sd
  * paired Wilcoxon signed-rank test (crossattn vs shared) across seeds
  * Ridge-on-fingerprint baseline (the classical benchmark reviewers ask for)
  * wrong-pocket ablation: cross-attention over a DIFFERENT receptor's pocket
    residues, same parameter count, to prove the gain comes from real pocket
    structure rather than from extra capacity.

Granular resume: results are flushed after every (protocol, receptor, arch, seed).

Outputs (data/real/):
  robust_results.json
  robust_report.md
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
from sklearn.linear_model import Ridge

RDLogger.DisableLog('rdApp.*')
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))
OUT = DATA

FP_BITS, FP_RADIUS = 2048, 2
N_TOKENS, TOKEN_DIM = 32, 64
D_MODEL, POCKET_DIM, N_HEADS, HIDDEN = 128, 128, 4, 256
DROPOUT = 0.2
LR_PEAK, WEIGHT_DECAY, CLIP = 5e-4, 1e-2, 1.0
BATCH, MAX_EPOCHS, PATIENCE, BOOT = 512, 70, 7, 1000
SEEDS = [0, 1, 2, 3, 4]
MIN_TRAIN = 800                      # cross-attention requires this many training molecules
ARCHS = ['shared', 'crossattn', 'crossattn_wrongpocket']


def set_seed(s):
    torch.manual_seed(s)
    np.random.seed(s)


torch.set_num_threads(os.cpu_count() or 4)


# ---------------------------------------------------------------------- data
def load_ligands():
    cache = os.path.join(DATA, 'ligand_fp_cache.npz')
    df = pd.read_csv(os.path.join(DATA, 'raw_activities.csv'))
    df['pchembl_value'] = pd.to_numeric(df['pchembl_value'], errors='coerce')
    df = df.dropna(subset=['pchembl_value', 'smiles'])
    df = (df.groupby(['gene', 'molecule_chembl_id'], as_index=False)
            .agg(pchembl=('pchembl_value', 'median'), smiles=('smiles', 'first')))
    z = np.load(cache, allow_pickle=True)
    assert len(z['smiles']) == len(df) and bool((z['smiles'] == df.smiles.values).all()), \
        'fingerprint cache is stale; delete data/real/ligand_fp_cache.npz and rerun'
    return df, z['fp'].astype(np.float32), z['scaffold']


def load_pockets(genes):
    z = np.load(os.path.join(DATA, 'residue_embeddings.npz'), allow_pickle=True)
    with open(os.path.join(DATA, 'pockets.json'), encoding='utf-8') as fh:
        pk = json.load(fh)['receptors']
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
    comps = Vt[:POCKET_DIM]
    var = float(((Xc @ comps.T) ** 2).sum() / (Xc ** 2).sum())
    P = max(m.shape[0] for m in raw.values())
    pocket = np.zeros((len(genes), P, POCKET_DIM), np.float32)
    mask = np.zeros((len(genes), P), np.float32)
    for i, g in enumerate(genes):
        m = raw[g]
        pocket[i, :m.shape[0]] = ((m - mu) @ comps.T).astype(np.float32)
        mask[i, :m.shape[0]] = 1.0
    # wrong-pocket control: receptor g is given the NEXT receptor's pocket
    n = len(genes)
    wrong = np.stack([pocket[(i + 1) % n] for i in range(n)])
    wrong_mask = np.stack([mask[(i + 1) % n] for i in range(n)])
    print('[ctx] pocket %s PCA(1280->%d) var=%.3f; wrong-pocket control built'
          % (pocket.shape, POCKET_DIM, var), flush=True)
    return pocket, mask, wrong, wrong_mask, {'variance_explained': round(var, 6),
                                             'pocket_sizes': {g: int(raw[g].shape[0]) for g in genes}}


# -------------------------------------------------------------------- models
class SharedMLP(nn.Module):
    def __init__(self, d_in, p):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d_in, HIDDEN), nn.GELU(), nn.Dropout(p),
                                 nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(p),
                                 nn.Linear(HIDDEN // 2, 1))

    def forward(self, fp, pocket, pmask):
        return self.net(fp).squeeze(-1)


class CrossAttn(nn.Module):
    def __init__(self, d_in, p):
        super().__init__()
        self.tok = nn.Sequential(nn.Linear(TOKEN_DIM, D_MODEL), nn.GELU())
        self.proj_kv = nn.Linear(POCKET_DIM, D_MODEL)
        self.attn = nn.MultiheadAttention(D_MODEL, N_HEADS, dropout=p, batch_first=True)
        self.lig = nn.Sequential(nn.Linear(d_in, D_MODEL), nn.GELU())
        self.head = nn.Sequential(nn.Linear(2 * D_MODEL, HIDDEN), nn.GELU(), nn.Dropout(p),
                                  nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(p),
                                  nn.Linear(HIDDEN // 2, 1))

    def forward(self, fp, pocket, pmask):
        b = fp.shape[0]
        q = self.tok(fp.view(b, N_TOKENS, TOKEN_DIM))
        kv = self.proj_kv(pocket)
        ctx, _ = self.attn(q, kv, kv, key_padding_mask=(pmask < 0.5), need_weights=False)
        return self.head(torch.cat([ctx.mean(dim=1), self.lig(fp)], dim=1)).squeeze(-1)


def build(arch, d_fp, p):
    return SharedMLP(d_fp, p) if arch == 'shared' else CrossAttn(d_fp, p)


# ------------------------------------------------------------------ training
def train_eval(arch, tr, va, te, FP, POCKET_T, PMASK_T, PIDX, y, seed):
    set_seed(seed)
    p = DROPOUT if len(tr) >= 2000 else 0.35
    model = build(arch, FP_BITS, p)
    opt = torch.optim.AdamW(model.parameters(), lr=LR_PEAK, weight_decay=WEIGHT_DECAY)
    y_t = torch.tensor(y, dtype=torch.float32)
    pid = torch.as_tensor(PIDX, dtype=torch.long)

    def batch(idx):
        ii = torch.as_tensor(np.asarray(idx), dtype=torch.long)
        g = pid[ii]
        return torch.from_numpy(FP[idx]), POCKET_T[g], PMASK_T[g], y_t[ii]

    n = len(tr)
    steps_per_epoch = max(1, int(np.ceil(n / BATCH)))
    total = MAX_EPOCHS * steps_per_epoch
    warm = max(1, int(0.05 * total))

    def lr_at(step):
        if step < warm:
            return LR_PEAK * step / warm
        prog = (step - warm) / max(1, total - warm)
        return LR_PEAK * 0.5 * (1 + np.cos(np.pi * prog))

    lossf = nn.SmoothL1Loss(beta=0.5)
    vf, vp, vm, vt = batch(va)
    best, state, bad, ep, step = 1e9, None, 0, 0, 0
    rng = np.random.default_rng(seed)
    for ep in range(MAX_EPOCHS):
        model.train()
        perm = rng.permutation(n)
        for b in range(0, n, BATCH):
            ii = tr[perm[b:b + BATCH]]
            f, pk, pm, t = batch(ii)
            for gparam in opt.param_groups:
                gparam['lr'] = lr_at(step)
            opt.zero_grad()
            loss = lossf(model(f, pk, pm), t)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            opt.step()
            step += 1
        model.eval()
        with torch.no_grad():
            vl = float(lossf(model(vf, vp, vm), vt))
        if np.isfinite(vl) and vl < best - 1e-5:
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
            f, pk, pm, _ = batch(te[b:b + 2048])
            preds.append(model(f, pk, pm).numpy())
    return np.concatenate(preds), ep + 1


def met(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {'pearson_r': float(stats.pearsonr(y, p)[0]),
            'spearman_rho': float(stats.spearmanr(y, p)[0]),
            'rmse': float(np.sqrt(np.mean((y - p) ** 2))), 'n': int(len(y))}


def boot_ci(y, p, n_boot=BOOT):
    rng = np.random.default_rng(0)
    n, rs = len(y), []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        if np.std(np.asarray(p)[i]) == 0:
            continue
        rs.append(stats.pearsonr(np.asarray(y)[i], np.asarray(p)[i])[0])
    a = np.array(rs)
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]


def scaffold_split(scaff, min_per=30):
    n = len(scaff)
    groups = {}
    for i, s in enumerate(scaff):
        groups.setdefault(s, []).append(i)
    order = sorted(groups, key=lambda k: -len(groups[k]))
    n_test, n_val = int(0.2 * n), int(0.15 * n)
    test, val = [], []
    for k in order:
        if len(test) + len(groups[k]) <= n_test:
            test.extend(groups[k])
        elif len(val) + len(groups[k]) <= n_val:
            val.extend(groups[k])
    used = set(test) | set(val)
    tr = [i for i in range(n) if i not in used]
    if min(len(tr), len(test), len(val)) < min_per:
        return None
    return np.array(tr), np.array(val), np.array(test)


def run_block(label, tr, va, te, FP, POCKET_T, PMASK_T, PIDX, y, store,
              WRONG_T=None, WRONG_M=None):
    """Run every architecture x seed for one split; flush after each seed."""
    cache = store.setdefault(label, {})
    for arch in ARCHS:
        # the wrong-pocket ablation uses identical parameters but a mismatched receptor pocket
        if arch == 'crossattn_wrongpocket' and WRONG_T is not None:
            use_pk, use_pm = WRONG_T, WRONG_M
        else:
            use_pk, use_pm = POCKET_T, PMASK_T
        if arch != 'shared' and len(tr) < MIN_TRAIN:
            cache[arch] = {'skipped': 'n_train=%d < MIN_TRAIN=%d' % (len(tr), MIN_TRAIN)}
            print('      %-22s SKIPPED (%d train < %d)' % (arch, len(tr), MIN_TRAIN), flush=True)
            continue
        rec = cache.get(arch) or {'seeds': []}
        done = {r['seed'] for r in rec['seeds']}
        # A fully-resumed block runs no seed at all, so `pred` would stay
        # unbound and the bootstrap below would raise UnboundLocalError.
        # Reset it per arch and only recompute the CI when we actually trained.
        pred = None
        for sd in SEEDS:
            if sd in done:
                continue
            t0 = time.time()
            pred, eps = train_eval(arch, tr, va, te, FP, use_pk, use_pm, PIDX, y, sd)
            m = met(y[te], pred)
            m['seed'] = sd
            m['epochs'] = int(eps)
            m['seconds'] = round(time.time() - t0, 1)
            rec['seeds'].append(m)
            cache[arch] = rec
            store['_flush']()
            print('      %-22s seed=%d r=%.3f (%.0fs)'
                  % (arch, sd, m['pearson_r'], m['seconds']), flush=True)
        # aggregate
        rs = [r['pearson_r'] for r in rec['seeds']]
        rec['mean_r'] = float(np.mean(rs))
        rec['sd_r'] = float(np.std(rs, ddof=1)) if len(rs) > 1 else 0.0
        # on a full resume no seed ran, so keep the CI stored by the run that
        # did the training instead of recomputing it from an unbound `pred`
        if pred is not None:
            rec['bootstrap_ci'] = boot_ci(y[te], pred)
        rec['n_train'], rec['n_test'] = int(len(tr)), int(len(te))
        cache[arch] = rec
        store['_flush']()

    # paired Wilcoxon across seeds: crossattn vs shared
    sh = cache.get('shared', {}).get('seeds', [])
    ca = cache.get('crossattn', {}).get('seeds', [])
    if sh and ca:
        a = np.array([r['pearson_r'] for r in sh])
        b = np.array([r['pearson_r'] for r in ca])
        if len(a) == len(b) and len(a) >= 3 and np.any(a != b):
            try:
                w = stats.wilcoxon(a, b)
                cache['wilcoxon_crossattn_vs_shared'] = {
                    'statistic': float(w.statistic), 'pvalue': float(w.pvalue),
                    'mean_diff': float((b - a).mean()), 'n_pairs': int(len(a))}
            except Exception as exc:                     # noqa: BLE001
                cache['wilcoxon_crossattn_vs_shared'] = {'error': str(exc)}
    # ridge baseline (deterministic; no seeds needed)
    try:
        rg = Ridge(alpha=1.0)
        rg.fit(FP[tr], y[tr])
        pr = rg.predict(FP[te])
        cache['ridge'] = met(y[te], pr)
        cache['ridge']['bootstrap_ci'] = boot_ci(y[te], pr)
    except Exception as exc:                             # noqa: BLE001
        cache['ridge'] = {'error': str(exc)}
    store['_flush']()


def block_complete(rec):
    """True only if EVERY arch in the block is skipped or holds all SEEDS.

    The previous guard tested only `shared.mean_r`, which is set as soon as the
    cheapest arm finishes. An interrupted block therefore looked "complete" on
    the next start and its remaining arms were silently skipped, leaving e.g.
    crossattn_wrongpocket aggregated over 2 seeds instead of 5.
    """
    if not isinstance(rec, dict):
        return False
    for arch in ARCHS:
        a = rec.get(arch)
        if not isinstance(a, dict):
            return False
        if 'skipped' in a:
            continue
        if len(a.get('seeds') or []) < len(SEEDS):
            return False
    return True


def main():
    t_start = time.time()
    df, FP, SCAFF = load_ligands()
    genes = sorted(df.gene.unique())
    y = df.pchembl.values.astype(np.float32)
    pocket, mask, wrong, wrong_mask, pca = load_pockets(genes)
    g2i = {g: i for i, g in enumerate(genes)}
    PIDX = np.array([g2i[g] for g in df.gene])
    PK_T, PM_T = torch.from_numpy(pocket), torch.from_numpy(mask)
    WK_T, WM_T = torch.from_numpy(wrong), torch.from_numpy(wrong_mask)
    print('[data] n=%d genes=%s' % (len(df), genes), flush=True)

    out_path = os.path.join(OUT, 'robust_results.json')
    store = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding='utf-8') as fh:
                store = json.load(fh)
            if store:                      # drop internal keys
                store = {k: v for k, v in store.items() if not k.startswith('_')}
        except Exception:                  # noqa: BLE001
            store = {}

    def flush():
        clean = {k: v for k, v in store.items() if not k.startswith('_')}
        clean.update({
            'purpose': 'Phase-1 robust measured evaluation (no simulation)',
            'seeds': SEEDS, 'archs': ARCHS, 'min_train': MIN_TRAIN,
            'optimizer': {'name': 'AdamW', 'lr_peak': LR_PEAK, 'weight_decay': WEIGHT_DECAY,
                          'clip_norm': CLIP, 'schedule': 'cosine with 5% warmup',
                          'dropout': DROPOUT, 'batch': BATCH,
                          'max_epochs': MAX_EPOCHS, 'patience': PATIENCE},
            'pocket_pca': pca,
        })
        with open(out_path, 'w', encoding='utf-8') as fh:
            json.dump(clean, fh, indent=2)

    store['_flush'] = flush
    flush()

    print('\n=== E3: scaffold-disjoint within-receptor ===', flush=True)
    for g in genes:
        idx = df.index[df.gene == g].values
        sp = scaffold_split(SCAFF[idx])
        if sp is None:
            print('  %-8s skipped (too few scaffolds)' % g, flush=True)
            continue
        tr, va, te = idx[sp[0]], idx[sp[1]], idx[sp[2]]
        print('  %-8s n_tr=%d n_va=%d n_te=%d' % (g, len(tr), len(va), len(te)), flush=True)
        run_block('E3|' + g, tr, va, te, FP, PK_T, PM_T, PIDX, y, store, WK_T, WM_T)

    print('\n=== E4: leave-one-receptor-out ===', flush=True)
    for held in genes:
        if block_complete(store.get('E4|' + held)):
            print('  %-8s [resume] complete' % held, flush=True)
            continue
        te = df.index[df.gene == held].values
        pool = df.index[df.gene != held].values
        rng = np.random.default_rng(42)
        perm = rng.permutation(len(pool))
        n_va = int(0.15 * len(pool))
        va, tr = pool[perm[:n_va]], pool[perm[n_va:]]
        print('  held-out %-8s n_tr=%d n_va=%d n_te=%d' % (held, len(tr), len(va), len(te)), flush=True)
        # wrong-pocket control uses the same architecture but a mismatched receptor pocket
        run_block('E4|' + held, tr, va, te, FP, PK_T, PM_T, PIDX, y, store, WK_T, WM_T)

    store.pop('_flush', None)
    flush()

    # ------------------------------------------------------------- markdown
    L = ['# MEG-BAR — Phase 1 robust measured evaluation', '',
         'Architectures: `shared` (fingerprint MLP), `crossattn` (ligand tokens attend to',
         'real pocket residues), `crossattn_wrongpocket` (identical model, mismatched',
         'receptor pocket), plus a Ridge-on-fingerprint baseline.',
         'Optimiser: AdamW, wd=%.2f, clip=%.1f, cosine LR with 5%% warmup, peak %g.'
         % (WEIGHT_DECAY, CLIP, LR_PEAK),
         'Five seeds (0-4); the cross-attention arm requires n_train >= %d.' % MIN_TRAIN, '']

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
    table('E4|', 'E4 — leave-one-receptor-out')
    L.append('Wall clock: %.1f s' % (time.time() - t_start))
    with open(os.path.join(OUT, 'robust_report.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')

    print('\n[OK] wrote robust_results.json + robust_report.md in %.1fs' % (time.time() - t_start), flush=True)


if __name__ == '__main__':
    sys.exit(main())
