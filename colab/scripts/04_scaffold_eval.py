#!/usr/bin/env python3
"""04_scaffold_eval.py — honest generalisation check with Bemis-Murcko scaffold splits.

A random molecule split lets close analogues sit on both sides, which inflates
Pearson r. This script repeats the within-receptor evaluation with a
scaffold-disjoint split, which is the harder and more honest protocol, and
writes the comparison for the manuscript.

Outputs (data/real/):
  scaffold_results.json
  scaffold_report.md
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

SEED = 42
FP_BITS, FP_RADIUS, HIDDEN, DROPOUT = 2048, 2, 256, 0.25
LR, BATCH, MAX_EPOCHS, PATIENCE, BOOT = 1e-3, 512, 90, 8, 1000

torch.manual_seed(SEED)
np.random.seed(SEED)
torch.set_num_threads(os.cpu_count() or 4)


class MLP(nn.Module):
    def __init__(self, d_in):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, HIDDEN), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(HIDDEN // 2, 1))

    def forward(self, x, ctx=None):
        return self.net(x).squeeze(-1)


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {
        'pearson_r': float(stats.pearsonr(y, p)[0]),
        'spearman_rho': float(stats.spearmanr(y, p)[0]),
        'rmse': float(np.sqrt(np.mean((y - p) ** 2))),
        'mae': float(np.mean(np.abs(y - p))),
        'n': int(len(y)),
    }


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


def train(model, xtr, ytr, xva, yva):
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    lossf = nn.SmoothL1Loss(beta=0.5)
    ytr_t, yva_t = torch.tensor(ytr, dtype=torch.float32), torch.tensor(yva, dtype=torch.float32)
    best, state, bad, ep = 1e9, None, 0, 0
    n = len(ytr)
    for ep in range(MAX_EPOCHS):
        model.train()
        perm = torch.randperm(n)
        for b in range(0, n, BATCH):
            idx = perm[b:b + BATCH]
            opt.zero_grad()
            loss = lossf(model(xtr[idx]), ytr_t[idx])
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            vl = float(lossf(model(xva), yva_t))
        if vl < best - 1e-5:
            best, bad, state = vl, 0, {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    if state:
        model.load_state_dict(state)
    model.eval()
    return model, ep + 1


def main():
    t0 = time.time()
    df = pd.read_csv(os.path.join(DATA, 'raw_activities.csv'))
    df['pchembl_value'] = pd.to_numeric(df['pchembl_value'], errors='coerce')
    df = df.dropna(subset=['pchembl_value', 'smiles'])
    df = (df.groupby(['gene', 'molecule_chembl_id'], as_index=False)
            .agg(pchembl=('pchembl_value', 'median'), smiles=('smiles', 'first')))

    mols, keep, scaff = [], [], []
    for i, smi in enumerate(df.smiles):
        m = Chem.MolFromSmiles(smi)
        if m is None:
            continue
        fp = AllChem.GetMorganFingerprintAsBitVect(m, FP_RADIUS, nBits=FP_BITS)
        arr = np.zeros((FP_BITS,), np.float32)
        AllChem.DataStructs.ConvertToNumpyArray(fp, arr)
        mols.append(arr)
        keep.append(i)
        scaff.append(MurckoScaffold.MurckoScaffoldSmiles(mol=m, includeChirality=False) or smi)
    df = df.iloc[keep].reset_index(drop=True)
    X = np.vstack(mols).astype(np.float32)
    y = df.pchembl.values.astype(np.float32)
    scaff = np.array(scaff)
    print('[data] n=%d  unique scaffolds=%d' % (len(df), len(set(scaff))), flush=True)

    out = {'split': 'Bemis-Murcko scaffold-disjoint', 'seed': SEED,
           'n_molecules': int(len(df)), 'n_unique_scaffolds': int(len(set(scaff))),
           'models': {}, 'completed_utc': datetime.now(timezone.utc).isoformat(timespec='seconds')}

    for g in sorted(df.gene.unique()):
        idx = df.index[df.gene == g].values
        if len(idx) < 120:
            print('  %-8s skipped (n=%d)' % (g, len(idx)), flush=True)
            continue
        sc = scaff[idx]
        groups = {}
        for j, s in enumerate(sc):
            groups.setdefault(s, []).append(j)
        order = sorted(groups, key=lambda k: -len(groups[k]))
        n = len(idx)
        n_test, n_val = int(0.2 * n), int(0.15 * n)
        test, val = [], []
        for k in order:
            if len(test) + len(groups[k]) <= n_test:
                test.extend(groups[k])
            elif len(val) + len(groups[k]) <= n_val:
                val.extend(groups[k])
        used = set(test) | set(val)
        train_j = [j for j in range(n) if j not in used]
        if min(len(train_j), len(test), len(val)) < 30:
            print('  %-8s skipped (train=%d val=%d test=%d)' % (g, len(train_j), len(val), len(test)), flush=True)
            continue
        Xtr, ytr = torch.tensor(X[idx[train_j]]), y[idx[train_j]]
        Xva, yva = torch.tensor(X[idx[val]]), y[idx[val]]
        Xte, yte = torch.tensor(X[idx[test]]), y[idx[test]]
        m, eps = train(MLP(FP_BITS), Xtr, ytr, Xva, yva)
        with torch.no_grad():
            pred = m(Xte).numpy()
        met = metrics(yte, pred)
        met['bootstrap'] = bootstrap(yte, pred)
        met['epochs'] = int(eps)
        met['n_train'], met['n_val'], met['n_test'] = len(train_j), len(val), len(test)
        met['test_scaffold_overlap_with_train'] = int(len(set(sc[test]) & set(sc[train_j])))
        out['models'][g] = met
        ci = met['bootstrap']['ci95']
        print('  %-8s n_train=%-5d n_test=%-4d  r=%.3f [%.3f,%.3f]  rho=%.3f  RMSE=%.3f  scaffold_overlap=%d'
              % (g, len(train_j), len(test), met['pearson_r'], ci[0], ci[1],
                 met['spearman_rho'], met['rmse'], met['test_scaffold_overlap_with_train']), flush=True)

    out['wall_clock_seconds'] = round(time.time() - t0, 1)
    with open(os.path.join(DATA, 'scaffold_results.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=2)

    lines = ['# MEG-BAR — scaffold-disjoint (honest) evaluation', '',
             'Split: Bemis-Murcko scaffold-disjoint. %d molecules, %d unique scaffolds.'
             % (out['n_molecules'], out['n_unique_scaffolds']), '',
             '| Receptor | n_train | n_test | Pearson r | 95% CI | Spearman | RMSE | shared scaffolds |',
             '|---|---|---|---|---|---|---|---|']
    for g, m in out['models'].items():
        ci = m['bootstrap']['ci95']
        lines.append('| %s | %d | %d | %.3f | [%.3f, %.3f] | %.3f | %.3f | %d |'
                     % (g, m['n_train'], m['n_test'], m['pearson_r'], ci[0], ci[1],
                        m['spearman_rho'], m['rmse'], m['test_scaffold_overlap_with_train']))
    lines += ['', 'Wall clock: %.1f s' % out['wall_clock_seconds']]
    with open(os.path.join(DATA, 'scaffold_report.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('\n[OK] wrote scaffold_results.json + scaffold_report.md in %.1fs' % out['wall_clock_seconds'])


if __name__ == '__main__':
    sys.exit(main())
