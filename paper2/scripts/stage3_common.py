"""Shared Stage 3 machinery: data loading, splits, models, training, and the
granular result store for the six model arms (Phases 16-21).

Arms (all trained with Paper 1's exact optimisation budget):
  shared                MLP on the Morgan fingerprint only          (Arm A)
  ridge                 Ridge on the fingerprint                    (Arm A baseline)
  crossattn_1d          Paper 1 cross-attention over structure-derived
                        pocket-residue ESM-2 embeddings, PCA 1280->128  (Arm B, 1D)
  pocket3d              pocket-graph encoder (distance-weighted message
                        passing) feeding the same cross-attention       (Arm C, 3D)
  dist_bias             pocket self-encoder with distance-biased attention
                        feeding the same cross-attention                (Arm D)
  pocket3d_wrongpocket  identical to pocket3d, pocket graph+features from the
                        NEXT receptor (sorted order)                    (Arm E, control)
  pocket3d_shuffled     identical to pocket3d, geometry permuted against
                        residue identity (fixed per-receptor permutation)(Arm F, control)

Non-negotiable 2: arms C, E, F share this module, the same store file, and the
same commit; the wrong-pocket-3D control can never lag the first 3D model.

All inputs are frozen artefacts: paper2/data/structures/pairs_41271.csv,
Paper 1 data/real/ligand_fp_cache_expanded.npz + residue_embeddings_expanded.npz,
and the Stage 2 feature files paper2/data/features/{SYM}_graph.npz.

Training runtime is local-only (torch + rdkit + sklearn); committed tests never
import this module.
"""

import gc
import json
import os
import sys
import time
import zlib
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
DATA_REAL = os.path.join(REPO, 'data', 'real')
STRUCT_DIR = os.path.join(REPO, 'paper2', 'data', 'structures')
FEATURE_DIR = os.path.join(REPO, 'paper2', 'data', 'features')
RESULTS_DIR = os.path.join(REPO, 'paper2', 'results', 'stage3')
STORE_PATH = os.path.join(RESULTS_DIR, 'arms_scaffold_results.json')

FP_BITS, FP_RADIUS = 2048, 2
N_TOKENS, TOKEN_DIM = 32, 64
D_MODEL, POCKET_DIM, N_HEADS, HIDDEN = 128, 128, 4, 256
DROPOUT = 0.2
LR_PEAK, WEIGHT_DECAY, CLIP = 5e-4, 1e-2, 1.0
BATCH, MAX_EPOCHS, PATIENCE, BOOT = 512, 70, 7, 1000
SEEDS = [0, 1, 2, 3, 4]
MIN_TRAIN = 800
EVAL_CHUNK = 2048
CONFIG = {'d_model': D_MODEL, 'batch': BATCH, 'max_epochs': MAX_EPOCHS,
          'lr_peak': LR_PEAK, 'pocket_dim': POCKET_DIM}

ARMS = ['shared', 'ridge', 'crossattn_1d', 'pocket3d', 'dist_bias',
        'pocket3d_wrongpocket', 'pocket3d_shuffled']
ATTENTION_ARMS = ['crossattn_1d', 'pocket3d', 'dist_bias',
                  'pocket3d_wrongpocket', 'pocket3d_shuffled']

torch.set_num_threads(os.cpu_count() or 4)


# ---------------------------------------------------------------------- data
def load_data():
    """Pair-level design matrices from frozen artefacts.

    Returns df (pairs_41271.csv), FP (n_pairs x 2048 float32, pair-level),
    y (pchembl medians), SCAFF (per-pair Bemis-Murcko scaffolds), genes.
    """
    import pandas as pd

    with open(os.path.join(STRUCT_DIR, 'pairs_41271.csv')) as fh:
        df = pd.read_csv(fh)
    z = np.load(os.path.join(DATA_REAL, 'ligand_fp_cache_expanded.npz'),
                allow_pickle=True)
    sm2row = {s: i for i, s in enumerate(z['smiles'].tolist())}
    fpid = np.array([sm2row[s] for s in df.smiles], dtype=np.int64)
    FP = z['fp'].astype(np.float32)[fpid]
    y = df.pchembl_median.values.astype(np.float32)
    SCAFF = z['scaffold'][fpid]
    genes = sorted(df.gene.unique())
    return df, FP, y, SCAFF, genes


def load_pocket_contexts(genes):
    """Structure-derived pocket contexts shared by every conditioning arm.

    Returns a dict with:
      pca        -- {'mu','comps','variance_explained','pocket_sizes'}
      PK, PM     -- (G, P, POCKET_DIM) PCA-reduced ESM-2 pocket tensors + mask
      NF         -- (G, P, 149) node features [pca128, aa one-hot 20, plddt/100]
      W          -- (G, P, P) row-normalised exp(-d/3) graph weights + self loop
      D          -- (G, P, P) true inter-residue distances (1e3 on padding)
      W_SHUF     -- (G, P, P) geometry-shuffled weights (fixed permutation)
      perm       -- per-gene permutation used for W_SHUF
    """
    from stage2_common import FEATURE_DIR as _FD  # noqa: F401  (import check)

    ze = np.load(os.path.join(DATA_REAL, 'residue_embeddings_expanded.npz'),
                 allow_pickle=True)
    with open(os.path.join(STRUCT_DIR, 'residue_mapping.json')) as fh:
        mapping = json.load(fh)['receptors']

    raw, onehot, plddt, graphs = {}, {}, {}, {}
    for g in genes:
        full = ze['%s_residues' % g]
        idx = mapping[g]['esm2_residue_indices_0based']
        raw[g] = full[idx].astype(np.float32)
        gz = np.load(os.path.join(FEATURE_DIR, '%s_graph.npz' % g))
        n = gz['x'].shape[0]
        if n != len(idx):
            raise SystemExit('graph node count %d != mapping %d for %s' % (n, len(idx), g))
        oh = np.zeros((n, 20), np.float32)
        aai = gz['aa_onehot_index']
        valid = aai >= 0
        oh[np.where(valid)[0], aai[valid]] = 1.0
        onehot[g] = oh
        plddt[g] = gz['plddt'].astype(np.float32)
        graphs[g] = (gz['edge_index'].astype(np.int64),
                     gz['edge_attr'].astype(np.float32))

    stack = np.vstack([raw[g] for g in genes])
    mu = stack.mean(axis=0, keepdims=True)
    Xc = stack - mu
    _, _, Vt = np.linalg.svd(Xc, full_matrices=False)
    comps = Vt[:POCKET_DIM]
    var = float(((Xc @ comps.T) ** 2).sum() / (Xc ** 2).sum())

    P = max(m.shape[0] for m in raw.values())
    G = len(genes)
    PK = np.zeros((G, P, POCKET_DIM), np.float32)
    PM = np.zeros((G, P), np.float32)
    NF = np.zeros((G, P, POCKET_DIM + 21), np.float32)
    W = np.zeros((G, P, P), np.float32)
    D = np.full((G, P, P), 1e3, np.float32)
    W_SHUF = np.zeros((G, P, P), np.float32)
    perm = {}
    for i, g in enumerate(genes):
        m = raw[g]
        n = m.shape[0]
        red = ((m - mu) @ comps.T).astype(np.float32)
        PK[i, :n] = red
        PM[i, :n] = 1.0
        NF[i, :n, :POCKET_DIM] = red
        NF[i, :n, POCKET_DIM:POCKET_DIM + 20] = onehot[g]
        NF[i, :n, POCKET_DIM + 20] = plddt[g] / 100.0
        ei, ea = graphs[g]
        dmat = np.full((n, n), 1e3, np.float32)
        wmat = np.zeros((n, n), np.float32)
        for (a, b), d in zip(ei.T, ea):
            dmat[a, b] = dmat[b, a] = d
            w = float(np.exp(-d / 3.0))
            wmat[a, b] = wmat[b, a] = max(wmat[a, b], w)
        np.fill_diagonal(wmat, 1.0)
        D[i, :n, :n] = dmat
        W[i, :n, :n] = wmat / wmat.sum(axis=1, keepdims=True)
        rng = np.random.default_rng(12345 + zlib.crc32(g.encode()))
        p = rng.permutation(n)
        perm[g] = p.tolist()
        ws = wmat[np.ix_(p, p)]
        W_SHUF[i, :n, :n] = ws / ws.sum(axis=1, keepdims=True)

    ctx = {
        'pca': {'variance_explained': round(var, 6),
                'pocket_sizes': {g: int(raw[g].shape[0]) for g in genes},
                'pca_components': POCKET_DIM, 'input_dim': int(stack.shape[1])},
        'PK': torch.from_numpy(PK), 'PM': torch.from_numpy(PM),
        'NF': torch.from_numpy(NF), 'W': torch.from_numpy(W),
        'D': torch.from_numpy(D), 'W_SHUF': torch.from_numpy(W_SHUF),
        'perm': perm,
    }
    print('[ctx] pocket (G=%d, P=%d) PCA(%d->%d) var=%.3f sizes=%s'
          % (G, P, stack.shape[1], POCKET_DIM, var, ctx['pca']['pocket_sizes']),
          flush=True)
    return ctx


# -------------------------------------------------------------------- models
class SharedMLP(nn.Module):
    def __init__(self, d_in, p):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d_in, HIDDEN), nn.GELU(), nn.Dropout(p),
                                 nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(p),
                                 nn.Linear(HIDDEN // 2, 1))

    def forward(self, fp, ctx, pid):
        return self.net(fp).squeeze(-1)


class CrossAttn1D(nn.Module):
    """Paper 1's CrossAttn, unchanged: ligand tokens cross-attend to
    PCA-reduced pocket-residue ESM-2 embeddings (1D conditioning)."""

    def __init__(self, d_in, p):
        super().__init__()
        self.tok = nn.Sequential(nn.Linear(TOKEN_DIM, D_MODEL), nn.GELU())
        self.proj_kv = nn.Linear(POCKET_DIM, D_MODEL)
        self.attn = nn.MultiheadAttention(D_MODEL, N_HEADS, dropout=p, batch_first=True)
        self.lig = nn.Sequential(nn.Linear(d_in, D_MODEL), nn.GELU())
        self.head = nn.Sequential(nn.Linear(2 * D_MODEL, HIDDEN), nn.GELU(), nn.Dropout(p),
                                  nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(p),
                                  nn.Linear(HIDDEN // 2, 1))

    def forward(self, fp, ctx, pid):
        b = fp.shape[0]
        pk, pm = ctx['PK'][pid], ctx['PM'][pid]
        q = self.tok(fp.view(b, N_TOKENS, TOKEN_DIM))
        kv = self.proj_kv(pk)
        attn_out, _ = self.attn(q, kv, kv, key_padding_mask=(pm < 0.5), need_weights=False)
        return self.head(torch.cat([attn_out.mean(dim=1), self.lig(fp)], dim=1)).squeeze(-1)


class GraphEncoderMixin(nn.Module):
    """Two rounds of distance-weighted message passing over the pocket graph."""

    def _enc_init(self, d_in):
        self.in_proj = nn.Linear(d_in, D_MODEL)
        self.conv1 = nn.Linear(D_MODEL, D_MODEL)
        self.conv2 = nn.Linear(D_MODEL, D_MODEL)

    def _enc_forward(self, nf, wmat):
        h = torch.nn.functional.gelu(self.in_proj(nf))
        h = torch.nn.functional.gelu(h + self.conv1(torch.bmm(wmat, h)))
        h = torch.nn.functional.gelu(h + self.conv2(torch.bmm(wmat, h)))
        return h


class Pocket3D(GraphEncoderMixin, nn.Module):
    """Arm C: pocket-graph encoder -> cross-attention (identical head to Arm B)."""

    def __init__(self, d_in, p):
        super().__init__()
        self._enc_init(POCKET_DIM + 21)
        self.tok = nn.Sequential(nn.Linear(TOKEN_DIM, D_MODEL), nn.GELU())
        self.attn = nn.MultiheadAttention(D_MODEL, N_HEADS, dropout=p, batch_first=True)
        self.lig = nn.Sequential(nn.Linear(d_in, D_MODEL), nn.GELU())
        self.head = nn.Sequential(nn.Linear(2 * D_MODEL, HIDDEN), nn.GELU(), nn.Dropout(p),
                                  nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(p),
                                  nn.Linear(HIDDEN // 2, 1))

    def forward(self, fp, ctx, pid):
        b = fp.shape[0]
        nf, wmat, pm = ctx['NF'][pid], ctx['W'][pid], ctx['PM'][pid]
        kv = self._enc_forward(nf, wmat)
        q = self.tok(fp.view(b, N_TOKENS, TOKEN_DIM))
        attn_out, _ = self.attn(q, kv, kv, key_padding_mask=(pm < 0.5), need_weights=False)
        return self.head(torch.cat([attn_out.mean(dim=1), self.lig(fp)], dim=1)).squeeze(-1)


class DistBiasEncoder(nn.Module):
    """Arm D: pocket self-attention whose logits are biased by the true
    inter-residue distances (learnable per-head scale, init 0)."""

    def __init__(self, d_in, p):
        super().__init__()
        self.in_proj = nn.Linear(d_in, D_MODEL)
        self.q1 = nn.Linear(D_MODEL, D_MODEL)
        self.k1 = nn.Linear(D_MODEL, D_MODEL)
        self.v1 = nn.Linear(D_MODEL, D_MODEL)
        self.o1 = nn.Linear(D_MODEL, D_MODEL)
        self.beta1 = nn.Parameter(torch.zeros(N_HEADS))
        self.q2 = nn.Linear(D_MODEL, D_MODEL)
        self.k2 = nn.Linear(D_MODEL, D_MODEL)
        self.v2 = nn.Linear(D_MODEL, D_MODEL)
        self.o2 = nn.Linear(D_MODEL, D_MODEL)
        self.beta2 = nn.Parameter(torch.zeros(N_HEADS))
        self.hd = D_MODEL // N_HEADS

    def _layer(self, h, dist, beta, qo, ko, vo, oo, B, P):
        q = qo(h).view(B, P, N_HEADS, self.hd).transpose(1, 2)
        k = ko(h).view(B, P, N_HEADS, self.hd).transpose(1, 2)
        v = vo(h).view(B, P, N_HEADS, self.hd).transpose(1, 2)
        logits = torch.matmul(q, k.transpose(-2, -1)) / (self.hd ** 0.5)
        logits = logits + beta.view(1, N_HEADS, 1, 1) * (-dist / 8.0).unsqueeze(1)
        a = torch.softmax(logits, dim=-1)
        out = torch.matmul(a, v).transpose(1, 2).reshape(B, P, D_MODEL)
        return h + oo(out)

    def forward(self, nf, dist):
        B, P = nf.shape[0], nf.shape[1]
        h = torch.nn.functional.gelu(self.in_proj(nf))
        h = self._layer(h, dist, self.beta1, self.q1, self.k1, self.v1, self.o1, B, P)
        h = self._layer(h, dist, self.beta2, self.q2, self.k2, self.v2, self.o2, B, P)
        return h


class DistBias3D(nn.Module):
    """Arm D full model: distance-biased pocket encoder -> same cross-attention."""

    def __init__(self, d_in, p):
        super().__init__()
        self.enc = DistBiasEncoder(POCKET_DIM + 21, p)
        self.tok = nn.Sequential(nn.Linear(TOKEN_DIM, D_MODEL), nn.GELU())
        self.attn = nn.MultiheadAttention(D_MODEL, N_HEADS, dropout=p, batch_first=True)
        self.lig = nn.Sequential(nn.Linear(d_in, D_MODEL), nn.GELU())
        self.head = nn.Sequential(nn.Linear(2 * D_MODEL, HIDDEN), nn.GELU(), nn.Dropout(p),
                                  nn.Linear(HIDDEN, HIDDEN // 2), nn.GELU(), nn.Dropout(p),
                                  nn.Linear(HIDDEN // 2, 1))

    def forward(self, fp, ctx, pid):
        b = fp.shape[0]
        nf, dist, pm = ctx['NF'][pid], ctx['D'][pid], ctx['PM'][pid]
        kv = self.enc(nf, dist)
        q = self.tok(fp.view(b, N_TOKENS, TOKEN_DIM))
        attn_out, _ = self.attn(q, kv, kv, key_padding_mask=(pm < 0.5), need_weights=False)
        return self.head(torch.cat([attn_out.mean(dim=1), self.lig(fp)], dim=1)).squeeze(-1)


def build(arch, d_fp, p):
    if arch == 'shared':
        return SharedMLP(d_fp, p)
    if arch == 'crossattn_1d':
        return CrossAttn1D(d_fp, p)
    if arch in ('pocket3d', 'pocket3d_wrongpocket', 'pocket3d_shuffled'):
        return Pocket3D(d_fp, p)
    if arch == 'dist_bias':
        return DistBias3D(d_fp, p)
    raise SystemExit('unknown arm %s' % arch)


# ------------------------------------------------------------------ training
def train_eval(arch, tr, va, te, FP, y, PIDX, ctx, seed):
    torch.manual_seed(seed)
    np.random.seed(seed)
    p = DROPOUT if len(tr) >= 2000 else 0.35
    model = build(arch, FP.shape[1], p)
    opt = torch.optim.AdamW(model.parameters(), lr=LR_PEAK, weight_decay=WEIGHT_DECAY)
    y_t = torch.tensor(y, dtype=torch.float32)
    pid_all = torch.as_tensor(PIDX, dtype=torch.long)
    if arch == 'pocket3d_wrongpocket':
        pid_all = (pid_all + 1) % len(ctx['PK'])
    if arch == 'pocket3d_shuffled':
        ctx = {**ctx, 'W': ctx['W_SHUF']}

    def batch(idx):
        ii = torch.as_tensor(np.asarray(idx), dtype=torch.long)
        return (torch.from_numpy(FP[idx]), ctx, pid_all[ii], y_t[ii])

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
    vf, vctx, vpid, vt = batch(va)
    best, state, bad, ep, step = 1e9, None, 0, 0, 0
    rng = np.random.default_rng(seed)
    for ep in range(MAX_EPOCHS):
        model.train()
        perm = rng.permutation(n)
        for b in range(0, n, BATCH):
            ii = tr[perm[b:b + BATCH]]
            f, cctx, gpid, t = batch(ii)
            for gp in opt.param_groups:
                gp['lr'] = lr_at(step)
            opt.zero_grad()
            loss = lossf(model(f, cctx, gpid), t)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            opt.step()
            step += 1
        model.eval()
        with torch.no_grad():
            vl = float(lossf(model(vf, vctx, vpid), vt))
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
        for b in range(0, len(te), EVAL_CHUNK):
            f, cctx, gpid, _ = batch(te[b:b + EVAL_CHUNK])
            preds.append(model(f, cctx, gpid).numpy())
    return np.concatenate(preds), ep + 1


def metrics(y, p):
    from scipy import stats
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {'pearson_r': float(stats.pearsonr(y, p)[0]),
            'spearman_rho': float(stats.spearmanr(y, p)[0]),
            'rmse': float(np.sqrt(np.mean((y - p) ** 2))),
            'mae': float(np.mean(np.abs(y - p))), 'n': int(len(y))}


def boot_ci(y, p, n_boot=BOOT):
    from scipy import stats
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
    """Paper 1's exact deterministic Bemis-Murcko split (largest scaffolds
    fill test 20% then val 15%; >=30 molecules per block)."""
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


# --------------------------------------------------------------------- store
class Store:
    """Granular resume store: flushed after every (receptor, arm, seed)."""

    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.data = {}
        if os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as fh:
                    self.data = json.load(fh)
            except Exception:                          # noqa: BLE001
                self.data = {}

    def flush(self, meta=None):
        if meta:
            self.data.update(meta)
        clean = {k: v for k, v in self.data.items() if not k.startswith('_')}
        clean['completed_utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
        with open(self.path, 'w', encoding='utf-8') as fh:
            json.dump(clean, fh, indent=2)

    def block(self, key):
        return self.data.setdefault(key, {})

    def run_receptor(self, key, arms, tr, va, te, FP, y, PIDX, ctx, ridge_fp=None):
        """Run every arm x seed for one split; flush after each seed."""
        cache = self.block(key)
        for arch in arms:
            if arch != 'shared' and arch != 'ridge' and len(tr) < MIN_TRAIN:
                if arch not in cache:
                    cache[arch] = {'skipped': 'n_train=%d < MIN_TRAIN=%d' % (len(tr), MIN_TRAIN)}
                    self.flush()
                print('      %-22s SKIPPED (%d train < %d)' % (arch, len(tr), MIN_TRAIN), flush=True)
                continue
            if arch == 'ridge':
                if 'ridge' in cache:
                    continue
                from sklearn.linear_model import Ridge
                rg = Ridge(alpha=1.0)
                rg.fit(FP[tr], y[tr])
                pr = rg.predict(FP[te])
                rec = metrics(y[te], pr)
                rec['bootstrap_ci'] = boot_ci(y[te], pr)
                cache['ridge'] = rec
                self.flush()
                print('      %-22s r=%.3f (deterministic)' % (arch, rec['pearson_r']), flush=True)
                continue
            rec = cache.get(arch) or {'seeds': []}
            stale = [r for r in rec['seeds'] if r.get('config', CONFIG) != CONFIG]
            if stale:
                rec['seeds'] = [r for r in rec['seeds'] if r.get('config', CONFIG) == CONFIG]
            done = {r['seed'] for r in rec['seeds']}
            pred = None
            te_y = None
            for sd in SEEDS:
                if sd in done:
                    continue
                t0 = time.time()
                pred, eps = train_eval(arch, tr, va, te, FP, y, PIDX, ctx, sd)
                te_y = y[te]
                m = metrics(y[te], pred)
                m['seed'] = sd
                m['epochs'] = int(eps)
                m['seconds'] = round(time.time() - t0, 1)
                m['config'] = dict(CONFIG)
                rec['seeds'].append(m)
                cache[arch] = rec
                self.flush()
                print('      %-22s seed=%d r=%.3f (%.0fs)'
                      % (arch, sd, m['pearson_r'], m['seconds']), flush=True)
            if pred is not None:
                rec['bootstrap_ci'] = boot_ci(te_y, pred)
                del pred
                gc.collect()
            rec['seeds'].sort(key=lambda r: r['seed'])
            rs = [r['pearson_r'] for r in rec['seeds']]
            rec['mean_r'] = float(np.mean(rs))
            rec['sd_r'] = float(np.std(rs, ddof=1)) if len(rs) > 1 else 0.0
            rec['n_train'], rec['n_test'] = int(len(tr)), int(len(te))
            cache[arch] = rec
            self.flush()


def receptor_splits(df, SCAFF, genes):
    """Per-receptor scaffold-disjoint splits (Paper 1 protocol)."""
    out = {}
    for g in genes:
        idx = df.index[df.gene == g].values
        sp = scaffold_split(SCAFF[idx])
        if sp is None:
            print('  %-8s skipped (too few scaffolds)' % g, flush=True)
            continue
        out[g] = (idx[sp[0]], idx[sp[1]], idx[sp[2]])
    return out


def pid_index(df, genes):
    g2i = {g: i for i, g in enumerate(genes)}
    return np.array([g2i[g] for g in df.gene], dtype=np.int64)


def temporal_splits(df, SCAFF, genes, cutoff=2015, min_train=120):
    """Paper 2's temporal protocol (pre-registered): train on documents older
    than the cutoff, test on documents from the cutoff onward. The validation
    block is a scaffold-disjoint 15% cut of the pre-cutoff pool (largest
    scaffolds first, Paper 1's split function); the pre-cutoff test block is
    folded back into training so only the post-cutoff era is ever tested.
    Receptors with <120 pre-cutoff or <30 post-cutoff pairs are skipped
    (GABRA1: 45 pre-2015 pairs - reported as skipped, never substituted)."""
    import pandas as pd

    out = {}
    years = pd.to_numeric(df.document_year, errors='coerce').values
    for g in genes:
        idx = df.index[df.gene == g].values
        yr = years[idx]
        te = idx[yr >= cutoff]
        pre = idx[yr < cutoff]
        if len(pre) < min_train or len(te) < 30:
            print('  %-8s temporal skipped (pre=%d post=%d)' % (g, len(pre), len(te)),
                  flush=True)
            continue
        sp = scaffold_split(SCAFF[pre])
        if sp is None:
            print('  %-8s temporal skipped (too few pre-cutoff scaffolds)' % g, flush=True)
            continue
        tr = np.concatenate([pre[sp[0]], pre[sp[2]]])
        out[g] = (tr, pre[sp[1]], te)
    return out


def run_arms(arms, extra_meta=None, protocol='E3', splits=None,
             store_path=None, ctx=None, purpose=None, proto_desc=None):
    """Shared entry point for the arm scripts: load frozen data, build
    contexts, run the requested arms across all receptors x seeds with
    granular resume, and flush the store.

    protocol='E3' (default) uses the scaffold-disjoint splits;
    protocol='E5' with splits=temporal_splits(...) writes the temporal store.
    ctx overrides the crystal pocket contexts (Stage 5: AFDB geometry or
    radius-sweep pockets); purpose/proto_desc override the store metadata.
    """
    t0 = time.time()
    df, FP, y, SCAFF, genes = load_data()
    if ctx is None:
        ctx = load_pocket_contexts(genes)
    PIDX = pid_index(df, genes)
    if splits is None:
        splits = receptor_splits(df, SCAFF, genes)
    if store_path is None:
        store_path = STORE_PATH
    store = Store(store_path)
    if purpose is None:
        if protocol == 'E3':
            purpose = ('Paper 2 Stage 3: six model arms on Paper 1\'s exact '
                       'scaffold-disjoint protocol (measured, no simulation)')
            proto_desc = 'E3-equivalent Bemis-Murcko scaffold-disjoint within-receptor'
        else:
            purpose = ('Paper 2 Stage 4 Phase 23: six model arms on the temporal '
                       'protocol, train pre-2015 / test 2015+ (measured)')
            proto_desc = ('E5 temporal: train document_year < 2015, val = '
                          'scaffold-disjoint 15% of the pre-cutoff pool, '
                          'test document_year >= 2015')
    store.flush({
        'purpose': purpose,
        'protocol': proto_desc,
        'data': {'n_pairs': int(len(df)), 'n_genes': len(genes),
                 'pairs_source': 'paper2/data/structures/pairs_41271.csv',
                 'fp_source': 'data/real/ligand_fp_cache_expanded.npz',
                 'pocket_source': 'paper2/data/structures/residue_mapping.json',
                 'graph_source': 'paper2/data/features/{SYM}_graph.npz'},
        'seeds': SEEDS, 'arms_requested': arms, 'min_train': MIN_TRAIN,
        'hyperparameters': dict(CONFIG, dropout=DROPOUT, patience=PATIENCE,
                                weight_decay=WEIGHT_DECAY, clip_norm=CLIP,
                                optimizer='AdamW, cosine LR with 5% warmup'),
        'pocket_pca': ctx.get('pca'),
        'shuffle_permutations': ctx.get('perm'),
    })
    if extra_meta:
        store.data.update(extra_meta)
    for g, (tr, va, te) in splits.items():
        print('  %-8s n_tr=%d n_va=%d n_te=%d' % (g, len(tr), len(va), len(te)), flush=True)
        store.run_receptor('%s|%s' % (protocol, g), arms, tr, va, te, FP, y, PIDX, ctx)
    store.flush()
    print('[OK] arms %s done in %.1fs -> %s'
          % (arms, time.time() - t0, os.path.relpath(store_path, REPO)), flush=True)
    return store
