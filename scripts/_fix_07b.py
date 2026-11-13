# -*- coding: utf-8 -*-
"""Patch 07_conditioned_model.py: memory-safe pocket handling + PCA + E4 resume.

Root cause of the OOM: `POCKET[PIDX[idx]]` fancy-indexes a (4,128,1280) array with a
15k-length index vector, materialising (15000,128,1280) float32 = 9.8 GB.

Fix:
  1. PCA-reduce pocket residue vectors 1280 -> 128 once, offline (documented).
  2. Keep pockets as per-gene tensors and gather only inside the batch loop.
  3. Resume: if E3 is already in conditioned_results.json, skip it and run E4.
"""
import io
import re

P = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\scripts\real\07_conditioned_model.py'
s = io.open(P, encoding='utf-8').read()

# ---------------------------------------------------------------- 1. constants
s = s.replace("D_MODEL = 128", "D_MODEL = 128\nPOCKET_DIM = 128      # PCA-reduced pocket residue dimension")

# --------------------------------------------------- 2. replace load_contexts
old_lc_start = s.index("def load_contexts(genes):")
old_lc_end = s.index("# -------------------------------------------------------------------- models")
new_lc = '''def load_contexts(genes):
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


'''
s = s[:old_lc_start] + new_lc + s[old_lc_end:]

# ------------------------------------------- 3. patch CrossAttentionConditioned
s = s.replace("""    def __init__(self, d_in, d_res, d_model=D_MODEL, n_heads=N_HEADS):""",
              """    def __init__(self, d_in, d_res, d_model=D_MODEL, n_heads=N_HEADS):""")
s = s.replace("        self.proj_kv = nn.Linear(d_res, d_model)",
              "        self.proj_kv = nn.Linear(d_res, d_model)   # d_res == POCKET_DIM after PCA")

# ------------------------------------------------- 4. replace train_eval (memory)
te_start = s.index("def train_eval(")
te_end = s.index("def scaffold_groups(")
new_te = '''def train_eval(model, tr, va, te, FP, CONST, POCKET_T, PMASK_T, PIDX, y, verbose=False):
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


'''
s = s[:te_start] + new_te + s[te_end:]

# ------------------------------------------------------------- 5. main() rewrite
m_start = s.index("def main():")
m_end = s.index("if __name__ == '__main__':")
new_main = '''def main():
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

    if not res['E3_scaffold_within_receptor']:
        print('\\n=== E3: scaffold-disjoint within-receptor ===', flush=True)
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
                m = build(arch, FP_BITS, d_pocket)
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

    print('\\n=== E4: leave-one-receptor-out ===', flush=True)
    for held in genes:
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
            m = build(arch, FP_BITS, d_pocket)
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
        fh.write('\\n'.join(L) + '\\n')

    print('\\n[OK] wrote conditioned_results.json + conditioned_report.md in %.1fs'
          % res['wall_clock_seconds'], flush=True)


'''
s = s[:m_start] + new_main + s[m_end:]

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('rewrote 07_conditioned_model.py with memory-safe batching + PCA + resume')
