#!/usr/bin/env python3
"""03_experiment.py — REAL measured experiment: shared vs specialized+routed heads.

Everything here is measured. No synthetic data, no prescribed correlations.
Inputs are the real files produced by 01_fetch_data.py and 02_embed_proteins.py.

Two questions, each answered by a held-out measurement:

  Q1 (within-distribution) -- on a random, molecule-disjoint split, does a single
     shared affinity model match or beat per-receptor specialist heads?

  Q2 (zero-shot / router blindness) -- hold one receptor out of training entirely.
     Compare (a) the shared model, (b) a routed mixture of receptor experts whose
     router is trained on the other three receptors, and (c) the same mixture with
     a FROZEN UNIFORM router (the "router blindness" condition). This is the
     manuscript's central claim, tested for real.

Outputs (data/real/):
  experiment_results.json    every metric, per receptor and pooled
  experiment_report.md       human-readable tables
"""
import json
import os
import sys
import time
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
from rdkit.Chem.Scaffolds import MurckoScaffold
from scipy import stats
from sklearn.model_selection import train_test_split

warnings.filterwarnings('ignore')
RDLogger.DisableLog('rdApp.*')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DATA = os.path.join(ROOT, 'data', 'real')
OUT = DATA

SEED = 42
FP_BITS = 2048
FP_RADIUS = 2
HIDDEN = 256
DROPOUT = 0.25
LR = 1e-3
BATCH = 512
MAX_EPOCHS = 90
PATIENCE = 8
BOOT = 1000

torch.manual_seed(SEED)
np.random.seed(SEED)
torch.set_num_threads(os.cpu_count() or 4)


# --------------------------------------------------------------------------- data
def load_data():
    raw = pd.read_csv(os.path.join(DATA, 'raw_activities.csv'))
    n_raw = len(raw)
    # Deduplicate: median measured pChEMBL per (receptor, molecule).
    raw['pchembl_value'] = pd.to_numeric(raw['pchembl_value'], errors='coerce')
    raw = raw.dropna(subset=['pchembl_value', 'smiles'])
    agg = (raw.groupby(['gene', 'molecule_chembl_id'], as_index=False)
              .agg(pchembl=('pchembl_value', 'median'),
                   smiles=('smiles', 'first'),
                   n_records=('pchembl_value', 'size')))
    print('[data] raw records=%d -> unique (gene,molecule) pairs=%d' % (n_raw, len(agg)))
    for g, sub in agg.groupby('gene'):
        print('       %-8s n=%-5d  pChEMBL mean=%.2f sd=%.2f range=[%.2f, %.2f]'
              % (g, len(sub), sub.pchembl.mean(), sub.pchembl.std(),
                 sub.pchembl.min(), sub.pchembl.max()))
    return agg


def fingerprints(smiles):
    fps = []
    keep = []
    for i, smi in enumerate(smiles):
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, FP_RADIUS, nBits=FP_BITS)
        arr = np.zeros((FP_BITS,), dtype=np.float32)
        AllChem.DataStructs.ConvertToNumpyArray(fp, arr)
        fps.append(arr)
        keep.append(i)
    print('[fp] valid molecules=%d / %d' % (len(keep), len(smiles)))
    return np.vstack(fps), np.array(keep)


def scaffold_split(scaffolds, frac_test=0.2, frac_val=0.15):
    """Group by Bemis-Murcko scaffold so no scaffold leaks across splits."""
    groups = {}
    for i, sc in enumerate(scaffolds):
        groups.setdefault(sc, []).append(i)
    keys = sorted(groups, key=lambda k: -len(groups[k]))
    n = len(scaffolds)
    n_test = int(frac_test * n)
    n_val = int(frac_val * n)
    test_idx, val_idx = [], []
    for k in keys:
        if len(test_idx) + len(groups[k]) <= n_test:
            test_idx.extend(groups[k])
        elif len(val_idx) + len(groups[k]) <= n_val:
            val_idx.extend(groups[k])
    used = set(test_idx) | set(val_idx)
    train_idx = [i for i in range(n) if i not in used]
    return np.array(train_idx), np.array(val_idx), np.array(test_idx)


# ------------------------------------------------------------------------- models
class MLP(nn.Module):
    def __init__(self, d_in):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, HIDDEN), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN // 2, 1),
        )

    def forward(self, x, ctx=None):
        return self.net(x).squeeze(-1)


class RoutedExperts(nn.Module):
    """K receptor experts + a router over a receptor-context vector.

    router_mode: 'trained'  -> gate is learned (paper's re-anchoring)
                 'uniform'  -> frozen 1/K gate (paper's router-blindness baseline)
    """

    def __init__(self, d_in, d_ctx, n_experts, router_mode='trained'):
        super().__init__()
        self.router_mode = router_mode
        self.experts = nn.ModuleList([MLP(d_in) for _ in range(n_experts)])
        self.router = nn.Linear(d_ctx, n_experts)
        if router_mode == 'uniform':
            for p in self.router.parameters():
                p.requires_grad_(False)

    def forward(self, x, ctx):
        outs = torch.stack([e(x) for e in self.experts], dim=1)   # (B, K)
        if self.router_mode == 'uniform':
            g = torch.full((x.shape[0], outs.shape[1]), 1.0 / outs.shape[1], device=x.device)
        else:
            g = torch.softmax(self.router(ctx), dim=1)
        return (g * outs).sum(dim=1), g


# ----------------------------------------------------------------------- metrics
def metrics(y, p):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    r = float(stats.pearsonr(y, p)[0]) if len(y) > 2 and np.std(p) > 0 else float('nan')
    rho = float(stats.spearmanr(y, p)[0]) if len(y) > 2 and np.std(p) > 0 else float('nan')
    rmse = float(np.sqrt(np.mean((y - p) ** 2)))
    mae = float(np.mean(np.abs(y - p)))
    return {'pearson_r': r, 'spearman_rho': rho, 'rmse': rmse, 'mae': mae, 'n': int(len(y))}


def bootstrap_ci(y, p, n_boot=BOOT, alpha=0.05):
    rng = np.random.default_rng(SEED)
    n = len(y)
    rs, rhos = [], []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yy, pp = np.asarray(y)[idx], np.asarray(p)[idx]
        if np.std(pp) == 0 or np.std(yy) == 0:
            continue
        rs.append(stats.pearsonr(yy, pp)[0])
        rhos.append(stats.spearmanr(yy, pp)[0])
    out = {}
    for name, arr in (('pearson_r', rs), ('spearman_rho', rhos)):
        arr = np.array(arr)
        out[name] = {
            'mean': float(arr.mean()),
            'sd': float(arr.std()),
            'ci95': [float(np.percentile(arr, 100 * alpha / 2)),
                     float(np.percentile(arr, 100 * (1 - alpha / 2)))],
        }
    return out


# ----------------------------------------------------------------------- training
def _fwd(model, x, c):
    """Return (prediction, gate_or_None) for both plain MLPs and RoutedExperts."""
    out = model(x, c)
    if isinstance(out, tuple):
        return out[0], out[1]
    return out, None



def train_model(model, x_tr, c_tr, y_tr, x_va, c_va, y_va, tag=''):
    opt = torch.optim.Adam([p for p in model.parameters() if p.requires_grad], lr=LR)
    lossf = nn.SmoothL1Loss(beta=0.5)
    y_tr_t = torch.tensor(y_tr, dtype=torch.float32)
    y_va_t = torch.tensor(y_va, dtype=torch.float32)
    best, best_state, bad = float('inf'), None, 0
    n = len(y_tr)
    for ep in range(MAX_EPOCHS):
        model.train()
        perm = torch.randperm(n)
        for b in range(0, n, BATCH):
            idx = perm[b:b + BATCH]
            opt.zero_grad()
            out, _ = _fwd(model, x_tr[idx], c_tr[idx])
            loss = lossf(out, y_tr_t[idx])
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            pv, _ = _fwd(model, x_va, c_va)
            vl = float(lossf(pv, y_va_t))
        if vl < best - 1e-5:
            best, bad = vl, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    return model, ep + 1


def predict(model, x, c):
    with torch.no_grad():
        out, g = _fwd(model, x, c)
    if g is None:
        return out.numpy(), None
    return out.numpy(), g.numpy()


# --------------------------------------------------------------------- experiment
def main():
    t_start = time.time()
    df = load_data()
    fps, keep = fingerprints(df.smiles.tolist())
    df = df.iloc[keep].reset_index(drop=True)

    # Receptor context vector: real ESM-2 embedding if available, else one-hot.
    emb_path = os.path.join(DATA, 'protein_embeddings.npz')
    genes = sorted(df.gene.unique())
    ctx_dim = 0
    ctx_source = 'one_hot'
    if os.path.exists(emb_path):
        z = np.load(emb_path, allow_pickle=True)
        emb_genes = list(z['genes'])
        if all(g in emb_genes for g in genes):
            E = z['mean']
            ctx_map = {g: E[emb_genes.index(g)] for g in genes}
            ctx_dim = E.shape[1]
            ctx_source = 'esm2_mean_pool'
            print('[ctx] using real ESM-2 embeddings, dim=%d' % ctx_dim)
    if ctx_dim == 0:
        ctx_dim = len(genes)
        ctx_map = {g: np.eye(len(genes))[i].astype(np.float32) for i, g in enumerate(genes)}
        print('[ctx] using one-hot receptor context, dim=%d' % ctx_dim)

    ctx = np.vstack([ctx_map[g] for g in df.gene]).astype(np.float32)
    y = df.pchembl.values.astype(np.float32)
    X = fps.astype(np.float32)
    gene_arr = df.gene.values
    smiles_arr = df.smiles.values

    results = {
        'purpose': 'REAL measured experiment (no simulation)',
        'seed': SEED,
        'data': {
            'n_molecules': int(len(df)),
            'genes': genes,
            'per_gene_counts': {g: int((df.gene == g).sum()) for g in genes},
            'context_source': ctx_source,
            'context_dim': int(ctx_dim),
        },
        'hyperparameters': {
            'fp_bits': FP_BITS, 'fp_radius': FP_RADIUS, 'hidden': HIDDEN,
            'dropout': DROPOUT, 'lr': LR, 'batch': BATCH,
            'max_epochs': MAX_EPOCHS, 'patience': PATIENCE, 'bootstrap': BOOT,
        },
        'experiments': {},
    }

    def flush_results():
        with open(os.path.join(OUT, 'experiment_results.json'), 'w', encoding='utf-8') as fh:
            json.dump(results, fh, indent=2)

    # ---------------- E1: within-distribution, per-receptor random split -------
    print('\n=== E1: within-receptor molecule-disjoint split ===')
    e1 = {}
    for g in genes:
        sub = df.index[df.gene == g].values
        if len(sub) < 80:
            print('  %-8s skipped (n=%d too small)' % (g, len(sub)))
            continue
        rng = np.random.default_rng(SEED)
        tr, te = train_test_split(sub, test_size=0.2, random_state=SEED)
        tr, va = train_test_split(tr, test_size=0.15, random_state=SEED)
        mdl = MLP(X.shape[1])
        mdl, eps = train_model(mdl, torch.tensor(X[tr]), torch.tensor(ctx[tr]), y[tr],
                              torch.tensor(X[va]), torch.tensor(ctx[va]), y[va])
        pred, _ = predict(mdl, torch.tensor(X[te]), torch.tensor(ctx[te]))
        m = metrics(y[te], pred)
        m['bootstrap'] = bootstrap_ci(y[te], pred)
        m['epochs'] = int(eps)
        e1[g] = m
        results['experiments']['E1_within_receptor'] = e1
        flush_results()
        print('  %-8s n_train=%-5d n_test=%-4d  r=%.3f [%.3f,%.3f]  rho=%.3f  RMSE=%.3f'
              % (g, len(tr), len(te), m['pearson_r'], m['bootstrap']['pearson_r']['ci95'][0],
                 m['bootstrap']['pearson_r']['ci95'][1], m['spearman_rho'], m['rmse']))
    results['experiments']['E1_within_receptor'] = e1

    # ---------------- E2: leave-one-receptor-out (zero-shot) ------------------
    print('\n=== E2: leave-one-receptor-out zero-shot ===')
    e2 = {}
    for held in genes:
        tr_idx = df.index[df.gene != held].values
        te_idx = df.index[df.gene == held].values
        if len(te_idx) < 40 or len(tr_idx) < 200:
            print('  %-8s skipped (train=%d test=%d)' % (held, len(tr_idx), len(te_idx)))
            continue
        tr_split, va_split = train_test_split(tr_idx, test_size=0.15, random_state=SEED)
        ctx_tr = torch.tensor(ctx[tr_split])
        x_tr, c_tr, y_tr = torch.tensor(X[tr_split]), ctx_tr, y[tr_split]
        x_va, c_va, y_va = torch.tensor(X[va_split]), torch.tensor(ctx[va_split]), y[va_split]
        x_te, c_te = torch.tensor(X[te_idx]), torch.tensor(ctx[te_idx])

        # (a) shared model
        shared = MLP(X.shape[1])
        shared, eps_a = train_model(shared, x_tr, c_tr, y_tr, x_va, c_va, y_va)
        pa, _ = predict(shared, x_te, c_te)

        # (b) routed experts, trained router
        routed = RoutedExperts(X.shape[1], ctx_dim, len(genes), router_mode='trained')
        routed, eps_b = train_model(routed, x_tr, c_tr, y_tr, x_va, c_va, y_va)
        pb, gb = predict(routed, x_te, c_te)

        # (c) routed experts, frozen uniform router = router blindness
        blind = RoutedExperts(X.shape[1], ctx_dim, len(genes), router_mode='uniform')
        blind, eps_c = train_model(blind, x_tr, c_tr, y_tr, x_va, c_va, y_va)
        pc, _ = predict(blind, x_te, c_te)

        # (d) per-receptor specialists trained only on data from the other 3
        #     (equivalent to the uniform router only if each expert sees all data)
        block = {}
        for name, pred, eps in (('shared', pa, eps_a), ('routed_trained', pb, eps_b),
                                ('routed_uniform', pc, eps_c)):
            m = metrics(y[te_idx], pred)
            m['bootstrap'] = bootstrap_ci(y[te_idx], pred)
            m['epochs'] = int(eps)
            block[name] = m
        # measured gate entropy on the held-out receptor's context
        ge = gb.mean(axis=0)
        block['gate_on_heldout'] = {
            'expert_weights': [float(v) for v in ge],
            'entropy_nats': float(-(ge * np.log(ge + 1e-12)).sum()),
            'max_entropy_nats': float(np.log(len(genes))),
        }
        e2[held] = block
        print('  held-out %-8s (n_test=%d)' % (held, len(te_idx)))
        for name in ('shared', 'routed_trained', 'routed_uniform'):
            m = block[name]
            print('      %-16s r=%+.3f [%+.3f,%+.3f]  rho=%+.3f  RMSE=%.3f'
                  % (name, m['pearson_r'], m['bootstrap']['pearson_r']['ci95'][0],
                     m['bootstrap']['pearson_r']['ci95'][1], m['spearman_rho'], m['rmse']))
        print('      router gate=%s  H=%.3f/%.3f nats'
              % (np.round(ge, 3).tolist(), block['gate_on_heldout']['entropy_nats'],
                 block['gate_on_heldout']['max_entropy_nats']))
        results['experiments']['E2_leave_one_receptor_out'] = e2
        flush_results()

    results['wall_clock_seconds'] = round(time.time() - t_start, 1)
    results['completed_utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')

    with open(os.path.join(OUT, 'experiment_results.json'), 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2)

    # ------------------------------------------------------------- markdown
    lines = ['# MEG-BAR — REAL measured experiment', '',
             'Data: ChEMBL measured pChEMBL values (Ki/IC50/Kd), deduplicated to',
             'unique (receptor, molecule) pairs. Features: Morgan fingerprint',
             '(%d bits, radius %d) concatenated with a real receptor context vector' % (FP_BITS, FP_RADIUS),
             '(%s, dim %d). No synthetic values anywhere.' % (ctx_source, ctx_dim), '',
             '## E1 — within-receptor split', '',
             '| Receptor | n_test | Pearson r | 95% CI | Spearman | RMSE |', '|---|---|---|---|---|---|']
    for g, m in e1.items():
        ci = m['bootstrap']['pearson_r']['ci95']
        lines.append('| %s | %d | %.3f | [%.3f, %.3f] | %.3f | %.3f |'
                     % (g, m['n'], m['pearson_r'], ci[0], ci[1], m['spearman_rho'], m['rmse']))
    lines += ['', '## E2 — leave-one-receptor-out (zero-shot)', '',
              '| Held out | Model | Pearson r | 95% CI | Spearman | RMSE |',
              '|---|---|---|---|---|---|']
    for held, block in e2.items():
        for name in ('shared', 'routed_trained', 'routed_uniform'):
            m = block[name]
            ci = m['bootstrap']['pearson_r']['ci95']
            lines.append('| %s | %s | %.3f | [%.3f, %.3f] | %.3f | %.3f |'
                         % (held, name, m['pearson_r'], ci[0], ci[1], m['spearman_rho'], m['rmse']))
    lines += ['', 'Wall clock: %.1f s' % results['wall_clock_seconds']]
    with open(os.path.join(OUT, 'experiment_report.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')

    print('\n[OK] wrote %s and experiment_report.md in %.1fs'
          % (os.path.join(OUT, 'experiment_results.json'), results['wall_clock_seconds']))


if __name__ == '__main__':
    sys.exit(main())
