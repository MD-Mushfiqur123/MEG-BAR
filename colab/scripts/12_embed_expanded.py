#!/usr/bin/env python3
"""12_embed_expanded.py — Phase 3: real ESM-2 embeddings + UniProt pockets for the expanded set.

Extends the Phase-1 conditioning pipeline to the eleven-receptor evidence base:
  1. UniProt feature annotations (same rules as 05_fetch_pockets.py) for the
     seven new receptors -> pockets_expanded.json (merged with the original four).
  2. Genuine frozen ESM-2 650M (facebook/esm2_t33_650M_UR50D) per-residue and
     mean/max-pooled embeddings for the seven new sequences on CPU.

Outputs (data/real/):
  pockets_expanded.json
  protein_embeddings_expanded.npz   (genes, mean, max) for all 11 receptors
  residue_embeddings_expanded.npz   (<GENE>_residues) for all 11 receptors
  residue_manifest_expanded.json
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))

ORIG_GENES = ['DRD2', 'HTR2A', 'GABRA1', 'CHRM1']
NEW = {
    'HTR1A': 'P08908',
    'DRD3': 'P35462',
    'ADRA2A': 'P08913',
    'ADRB2': 'P07550',
    'SERT': 'P31645',
    'DAT': 'Q01959',
    'HRH1': 'P35367',
}
UA = {'User-Agent': 'Mozilla/5.0 (MEG-BAR pocket annotation; academic use)'}
MAX_POCKET = 128
FLANK = 3
MODEL_ID = 'facebook/esm2_t33_650M_UR50D'


def fetch_entry(acc):
    url = 'https://rest.uniprot.org/uniprotkb/%s.json' % acc
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as fh:
                return json.loads(fh.read().decode('utf-8')), url
        except Exception:                     # noqa: BLE001
            time.sleep(2 * (attempt + 1))
    raise RuntimeError('failed to fetch %s' % url)


def collect(entry):
    binding, active, sites, tm = set(), set(), set(), []
    for f in entry.get('features', []):
        t = f.get('type')
        loc = f.get('location', {})
        start = (loc.get('start') or {}).get('value')
        end = (loc.get('end') or {}).get('value')
        if start is None or end is None:
            continue
        if t == 'Binding site':
            for d in f.get('ligands', []) or [{}]:
                if not d or d.get('name') in ('MLY', None):
                    continue
                binding.update(range(start, end + 1))
                break
            else:
                binding.update(range(start, end + 1))
        elif t == 'Active site':
            active.update(range(start, end + 1))
        elif t == 'Site':
            sites.update(range(start, end + 1))
        elif t == 'Transmembrane':
            tm.append((start, end))
    return binding, active, sites, tm


def build_pocket(entry):
    binding, active, sites, tm = collect(entry)
    chosen = binding | active
    used_from = 'binding+active'
    if not chosen:
        chosen = sites
        used_from = 'site'
    if not chosen:
        chosen = {s for lo, hi in tm for s in range(lo, hi + 1)}
        used_from = 'transmembrane'
    if not chosen:
        return None
    expanded = set()
    for r in chosen:
        for d in range(-FLANK, FLANK + 1):
            expanded.add(r + d)
    residues = sorted(r for r in expanded if 1 <= r <= int(entry['sequence']['length']))
    truncated = len(residues) > MAX_POCKET
    if truncated:
        step = len(residues) / MAX_POCKET
        residues = sorted({residues[min(int(i * step), len(residues) - 1)] for i in range(MAX_POCKET)})
    return {
        'uniprot': entry['primaryAccession'],
        'sequence_length': int(entry['sequence']['length']),
        'source_url': 'https://rest.uniprot.org/uniprotkb/%s.json' % entry['primaryAccession'],
        'annotation_counts': {
            'binding_sites': len(binding), 'active_sites': len(active),
            'site_features': len(sites), 'transmembrane_spans': len(tm),
        },
        'residues_used_from': used_from,
        'pocket_residue_count': len(residues),
        'pocket_truncated': truncated,
        'pocket_residues_1based': residues,
    }


def main():
    with open(os.path.join(DATA, 'proteins_expanded.json'), encoding='utf-8') as fh:
        proteins = json.load(fh)

    # ---- 1. pockets -------------------------------------------------------
    pk_path = os.path.join(DATA, 'pockets.json')
    with open(pk_path, encoding='utf-8') as fh:
        pockets = json.load(fh)
    out_pockets = {'purpose': pockets.get('purpose', 'UniProt binding-site annotations'),
                   'retrieved_utc': pockets.get('retrieved_utc'),
                   'flank': FLANK, 'max_pocket': MAX_POCKET,
                   'receptors': dict(pockets.get('receptors', {}))}
    for gene, acc in NEW.items():
        print('[pocket] %s (%s)' % (gene, acc), flush=True)
        entry, url = fetch_entry(acc)
        p = build_pocket(entry)
        p['source_url'] = url
        out_pockets['receptors'][gene] = p
        print('    residues used: %d (%s)' % (p['pocket_residue_count'], p['residues_used_from']), flush=True)
        time.sleep(0.5)
    with open(os.path.join(DATA, 'pockets_expanded.json'), 'w', encoding='utf-8') as fh:
        json.dump(out_pockets, fh, indent=2)
    print('[pocket] wrote pockets_expanded.json', flush=True)

    # ---- 2. ESM-2 embeddings ---------------------------------------------
    from transformers import AutoModel, AutoTokenizer

    device = 'cpu'
    torch.set_num_threads(os.cpu_count() or 4)
    print('[esm] loading %s on %s (%d threads)' % (MODEL_ID, device, torch.get_num_threads()), flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID)
    model.eval().to(device)

    pe = np.load(os.path.join(DATA, 'protein_embeddings.npz'), allow_pickle=True)
    re = np.load(os.path.join(DATA, 'residue_embeddings.npz'), allow_pickle=True)
    genes_all = sorted(set(ORIG_GENES) | set(NEW))
    mean_all, max_all = {}, {}
    res_all = {}
    for g in ORIG_GENES:
        i = list(pe['genes']).index(g)
        mean_all[g], max_all[g] = pe['mean'][i], pe['max'][i]
        res_all['%s_residues' % g] = re['%s_residues' % g]

    manifest = {
        'purpose': 'REAL ESM-2 embeddings for the expanded eleven-receptor set (no simulation)',
        'model_id': MODEL_ID,
        'checkpoint_source': 'https://huggingface.co/' + MODEL_ID,
        'parameters': int(sum(p.numel() for p in model.parameters())),
        'hidden_size': int(model.config.hidden_size),
        'layers': int(model.config.num_hidden_layers),
        'device': device,
        'torch_version': torch.__version__,
        'computed_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'per_gene': {},
    }

    for gene, acc in NEW.items():
        seq = proteins[gene]['sequence']
        t0 = time.time()
        enc = tok(seq, return_tensors='pt', add_special_tokens=True)
        with torch.no_grad():
            out = model(**enc).last_hidden_state[0]
        # strip special tokens; transformers ESM tokenizes <cls> + residues + <eos>
        emb = out[1:-1].numpy()
        assert emb.shape[0] == len(seq), 'token/residue mismatch for %s: %d vs %d' % (gene, emb.shape[0], len(seq))
        res_all['%s_residues' % gene] = emb.astype(np.float32)
        mean_all[gene] = emb.mean(axis=0).astype(np.float32)
        max_all[gene] = emb.max(axis=0).astype(np.float32)
        manifest['per_gene'][gene] = {
            'accession': acc, 'sequence_length': len(seq),
            'embedding_shape': list(emb.shape), 'seconds': round(time.time() - t0, 1),
        }
        print('[esm] %-8s len=%d  (%.0fs)' % (gene, len(seq), time.time() - t0), flush=True)

    np.savez_compressed(os.path.join(DATA, 'protein_embeddings_expanded.npz'),
                        genes=np.array(genes_all),
                        mean=np.stack([mean_all[g] for g in genes_all]),
                        max=np.stack([max_all[g] for g in genes_all]))
    np.savez_compressed(os.path.join(DATA, 'residue_embeddings_expanded.npz'),
                        **res_all)
    with open(os.path.join(DATA, 'residue_manifest_expanded.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2)
    print('[esm] wrote protein_embeddings_expanded.npz, residue_embeddings_expanded.npz', flush=True)


if __name__ == '__main__':
    sys.exit(main())
