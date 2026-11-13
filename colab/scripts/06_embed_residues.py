#!/usr/bin/env python3
"""06_embed_residues.py — REAL per-residue ESM-2 embeddings, full receptor length.

Unlike 02_embed_proteins.py (which mean-pools and therefore loses all positional
information), this keeps the full per-residue matrix so a ligand encoder can
cross-attend to specific pocket residues.

Output (data/real/):
  residue_embeddings.npz   {gene}_residues  float32 (L, 1280), residue i is row i
  residue_manifest.json    model id, shapes, layer, timings, hashes
"""
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))

MODEL_ID = 'facebook/esm2_t33_650M_UR50D'

import torch  # noqa: E402
from transformers import AutoModel, AutoTokenizer  # noqa: E402


def main():
    t0 = time.time()
    with io.open(os.path.join(DATA, 'proteins.json'), encoding='utf-8') as fh:
        proteins = json.load(fh)

    torch.set_num_threads(os.cpu_count() or 4)
    print('[*] loading %s' % MODEL_ID, flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID).eval()
    n_params = sum(p.numel() for p in model.parameters())
    print('[*] %.1fM params, hidden=%d, layers=%d'
          % (n_params / 1e6, model.config.hidden_size, model.config.num_hidden_layers), flush=True)

    arrays, meta = {}, {}
    for gene in sorted(proteins):
        seq = proteins[gene]['sequence']
        t1 = time.time()
        with torch.no_grad():
            enc = tok(seq, return_tensors='pt', truncation=True, max_length=1024)
            out = model(**enc)
            h = out.last_hidden_state[0]              # (L+2, d)
        # Drop CLS (index 0) and EOS (last); keep exactly len(seq) residue rows.
        res = h[1:1 + len(seq)].cpu().numpy().astype(np.float32)
        arrays['%s_residues' % gene] = res
        meta[gene] = {
            'sequence_length': len(seq),
            'embedding_shape': list(res.shape),
            'row_i_is_residue': 'i (0-based)',
            'seconds': round(time.time() - t1, 2),
            'row_norm_mean': float(np.linalg.norm(res, axis=1).mean()),
        }
        print('    %-8s residues=%d -> %s  (%.2fs)'
              % (gene, len(seq), res.shape, meta[gene]['seconds']), flush=True)

    npz_path = os.path.join(DATA, 'residue_embeddings.npz')
    np.savez_compressed(npz_path, **arrays)
    with open(npz_path, 'rb') as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()

    manifest = {
        'purpose': 'REAL per-residue ESM-2 embeddings for pocket conditioning (no simulation)',
        'model_id': MODEL_ID,
        'checkpoint_source': 'https://huggingface.co/' + MODEL_ID,
        'parameters': int(n_params),
        'hidden_size': int(model.config.hidden_size),
        'layers': int(model.config.num_hidden_layers),
        'device': 'cpu',
        'torch_version': torch.__version__,
        'per_gene': meta,
        'total_seconds': round(time.time() - t0, 2),
        'npz_sha256': digest,
        'completed_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }
    with io.open(os.path.join(DATA, 'residue_manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2)

    print('\n[OK] wrote %s in %.1fs' % (npz_path, manifest['total_seconds']))


if __name__ == '__main__':
    sys.exit(main())
