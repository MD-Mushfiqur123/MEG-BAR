#!/usr/bin/env python3
"""05_fetch_pockets.py — REAL binding-site annotations from UniProt.

The previous experiment's root cause was that a mean-pooled receptor embedding is
constant within a receptor, so the receptor never conditions the ligand. This
script extracts the actual annotated pocket residues so a ligand encoder can
cross-attend to them.

Source: UniProt REST  https://rest.uniprot.org/uniprotkb/<acc>.json
Nothing here is invented; residues come from UniProt feature annotations.

Output (data/real/):
  pockets.json   per gene: binding/active/site residues, transmembrane spans,
                 the expanded pocket residue list actually used, and provenance
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))

ACC = {
    'DRD2': 'P14416',
    'HTR2A': 'P28223',
    'GABRA1': 'P14867',
    'CHRM1': 'P11229',
}
UA = {'User-Agent': 'Mozilla/5.0 (MEG-BAR pocket annotation; academic use)'}
MAX_POCKET = 128      # cap so the attention is cheap on CPU
FLANK = 3             # expand each annotated residue by +/- flank in sequence


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
    """Return annotated residue sets, 1-based, from UniProt features."""
    kinds = {
        'binding_site': [], 'active_site': [], 'site': [],
        'transmembrane': [], 'region': [],
    }
    for f in entry.get('features', []):
        ftype = (f.get('type') or '').lower()
        loc = f.get('location') or {}
        start = (loc.get('start') or {}).get('value')
        end = (loc.get('end') or {}).get('value')
        if start is None:
            continue
        end = end if end is not None else start
        span = (int(start), int(end))
        if ftype == 'binding site':
            kinds['binding_site'].append(span)
        elif ftype == 'active site':
            kinds['active_site'].append(span)
        elif ftype == 'site':
            kinds['site'].append(span)
        elif ftype == 'transmembrane':
            kinds['transmembrane'].append(span)
        elif ftype == 'region of interest':
            kinds['region'].append(span)
    return kinds


def expand(spans, flank, seq_len):
    out = set()
    for a, b in spans:
        lo = max(1, a - flank)
        hi = min(seq_len, b + flank)
        out.update(range(lo, hi + 1))
    return out


def main():
    with open(os.path.join(DATA, 'proteins.json'), encoding='utf-8') as fh:
        proteins = json.load(fh)

    result = {
        'purpose': 'REAL UniProt binding-site annotations for receptor conditioning',
        'retrieved_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'flank': FLANK, 'max_pocket': MAX_POCKET,
        'receptors': {},
    }

    for gene, acc in ACC.items():
        seq = proteins[gene]['sequence']
        entry, url = fetch_entry(acc)
        kinds = collect(entry)
        n_bind = sum(b - a + 1 for a, b in kinds['binding_site'])
        n_act = sum(b - a + 1 for a, b in kinds['active_site'])
        n_tm = sum(b - a + 1 for a, b in kinds['transmembrane'])
        print('[*] %-7s %s  binding_spans=%d (%d res)  active=%d (%d res)  tm_spans=%d (%d res)'
              % (gene, acc, len(kinds['binding_site']), n_bind,
                 len(kinds['active_site']), n_act,
                 len(kinds['transmembrane']), n_tm), flush=True)

        core = expand(kinds['binding_site'] + kinds['active_site'], FLANK, len(seq))
        # If annotation is thin, fall back to annotated 'site' spans, then to TM spans.
        if len(core) < 24 and kinds['site']:
            core |= expand(kinds['site'], FLANK, len(seq))
        used = 'binding+active'
        if len(core) < 24 and kinds['transmembrane']:
            core |= expand(kinds['transmembrane'], 0, len(seq))
            used = 'binding+active+transmembrane'

        pocket = sorted(core)
        truncated = False
        if len(pocket) > MAX_POCKET:
            step = len(pocket) / float(MAX_POCKET)
            pocket = [pocket[int(i * step)] for i in range(MAX_POCKET)]
            truncated = True

        result['receptors'][gene] = {
            'uniprot': acc,
            'sequence_length': len(seq),
            'source_url': url,
            'annotation_counts': {
                'binding_sites': len(kinds['binding_site']),
                'active_sites': len(kinds['active_site']),
                'site_features': len(kinds['site']),
                'transmembrane_spans': len(kinds['transmembrane']),
            },
            'residues_used_from': used,
            'pocket_residue_count': len(pocket),
            'pocket_truncated': truncated,
            'pocket_residues_1based': pocket,
            'pocket_sequence': ''.join(seq[i - 1] for i in pocket),
        }
        print('      -> pocket residues: %d (%s)%s'
              % (len(pocket), used, ' [truncated]' if truncated else ''), flush=True)
        time.sleep(0.6)

    out = os.path.join(DATA, 'pockets.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, indent=2)
    print('\n[OK] wrote %s' % out)


if __name__ == '__main__':
    sys.exit(main())
