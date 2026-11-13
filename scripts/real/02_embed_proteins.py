#!/usr/bin/env python3
"""02_embed_proteins.py — REAL ESM-2 embeddings of the four receptor sequences.

Downloads the genuine ESM-2 checkpoint from HuggingFace and runs it on the four
UniProt receptor sequences fetched by 01_fetch_data.py. Nothing is simulated.

Outputs (under data/real/):
  protein_embeddings.npz   mean-pooled + max-pooled layer-33 embeddings per gene
  embed_manifest.json      model id, vocab, hidden size, layers, param count,
                           sequence hashes, wall-clock, sha256 of outputs
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
OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))
os.makedirs(OUT, exist_ok=True)

# esm2_t33_650M_UR50D is the checkpoint named in the manuscript.
MODEL_ID = 'facebook/esm2_t33_650M_UR50D'
FALLBACK_ID = 'facebook/esm2_t30_150M_UR50D'

import torch  # noqa: E402
from transformers import AutoModel, AutoTokenizer  # noqa: E402


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def embed(seq, model, tok, device):
    """Mean- and max-pooled final-layer representation, fp32, length-independent."""
    with torch.no_grad():
        enc = tok(seq, return_tensors='pt', truncation=True, max_length=1024)
        enc = {k: v.to(device) for k, v in enc.items()}
        out = model(**enc)
        h = out.last_hidden_state[0]            # (L+2, d) incl. CLS/EOS
        mask = enc['attention_mask'][0].bool()
        h = h[mask]                              # drop padding
        mean_pool = h.mean(dim=0)
        max_pool = h.max(dim=0).values
        return mean_pool.cpu().numpy(), max_pool.cpu().numpy(), int(mask.sum())


def main():
    t0 = time.time()
    with io.open(os.path.join(OUT, 'proteins.json'), encoding='utf-8') as fh:
        proteins = json.load(fh)

    device = torch.device('cpu')
    torch.set_num_threads(os.cpu_count() or 4)

    model_id = MODEL_ID
    print('[*] loading %s (real weights from HuggingFace)' % model_id, flush=True)
    try:
        tok = AutoTokenizer.from_pretrained(model_id)
        model = AutoModel.from_pretrained(model_id)
    except Exception as exc:                     # noqa: BLE001
        print('[!] primary checkpoint unavailable (%s); falling back to %s' % (exc, FALLBACK_ID), flush=True)
        model_id = FALLBACK_ID
        tok = AutoTokenizer.from_pretrained(model_id)
        model = AutoModel.from_pretrained(model_id)

    model.eval().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    dim = model.config.hidden_size
    layers = model.config.num_hidden_layers
    print('[*] loaded %s | layers=%d hidden=%d params=%.1fM' % (model_id, layers, dim, n_params / 1e6), flush=True)

    means, maxes, genes, meta = [], [], [], {}
    for gene in sorted(proteins):
        p = proteins[gene]
        seq = p['sequence']
        t1 = time.time()
        m, x, ntok = embed(seq, model, tok, device)
        dt = time.time() - t1
        means.append(m)
        maxes.append(x)
        genes.append(gene)
        meta[gene] = {
            'accession': p['accession'],
            'sequence_length': len(seq),
            'tokens_used': ntok,
            'sequence_sha256': sha256_bytes(seq.encode('utf-8')),
            'embed_seconds': round(dt, 3),
        }
        print('    %-8s len=%-4d tokens=%-4d embed=%.2fs norm=%.4f'
              % (gene, len(seq), ntok, dt, float(np.linalg.norm(m))), flush=True)

    npz_path = os.path.join(OUT, 'protein_embeddings.npz')
    np.savez_compressed(
        npz_path,
        genes=np.array(genes),
        mean=np.vstack(means),
        max=np.vstack(maxes),
    )

    total = time.time() - t0
    with open(npz_path, 'rb') as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()

    manifest = {
        'purpose': 'REAL ESM-2 embeddings of receptor sequences (no simulation)',
        'model_id': model_id,
        'requested_model_id': MODEL_ID,
        'checkpoint_source': 'https://huggingface.co/' + model_id,
        'layers': layers,
        'hidden_size': dim,
        'parameters': int(n_params),
        'device': 'cpu',
        'torch_threads': int(torch.get_num_threads()),
        'torch_version': torch.__version__,
        'dtype': 'float32',
        'pooling': ['mean_over_residues', 'max_over_residues'],
        'per_gene': meta,
        'total_seconds': round(total, 2),
        'npz_sha256': digest,
        'completed_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }
    with io.open(os.path.join(OUT, 'embed_manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2)

    print('\n[OK] wrote %s  shape=%s  (%d genes, %.1fM params, %.1fs total)'
          % (npz_path, np.vstack(means).shape, len(genes), n_params / 1e6, total))


if __name__ == '__main__':
    sys.exit(main())
