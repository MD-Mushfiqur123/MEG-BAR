#!/usr/bin/env python3
"""01_fetch_data.py — fetch REAL measured bioactivity data + REAL protein sequences.

Sources (all live, none simulated):
  * ChEMBL REST API  https://www.ebi.ac.uk/chembl/api/data/activity.json
  * UniProt REST API https://rest.uniprot.org/uniprotkb/<acc>.fasta

Outputs (under data/real/):
  raw_activities.csv   one row per measured affinity record
  proteins.json        {gene: {"accession", "sequence", "length"}}
  fetch_manifest.json  exact query URLs, counts, timestamps, SHA256 of outputs
"""
import csv
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))
os.makedirs(OUT, exist_ok=True)

CHEMBL = 'https://www.ebi.ac.uk/chembl/api/data/activity.json'
UNIPROT = 'https://rest.uniprot.org/uniprotkb/{acc}.fasta'

TARGETS = [
    # gene,  chembl target id, uniprot,  display name
    ('DRD2',  'CHEMBL217', 'P14416', 'Dopamine D2 receptor'),
    ('HTR2A', 'CHEMBL224', 'P28223', 'Serotonin 5-HT2A receptor'),
    ('GABRA1', 'CHEMBL1962', 'P14867', 'GABA-A receptor subunit alpha-1'),
    ('CHRM1', 'CHEMBL216', 'P11229', 'Muscarinic acetylcholine receptor M1'),
]

ACTIVITY_TYPES = ['Ki', 'IC50', 'Kd']
PAGE = 1000
UA = {'User-Agent': 'Mozilla/5.0 (MEG-BAR real-data experiment; academic use)'}


def get_json(url, tries=4):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as fh:
                return json.loads(fh.read().decode('utf-8'))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError('GET failed: %s (%s)' % (url, last))


def fetch_target(gene, tid, atype):
    """Page through the ChEMBL activity endpoint for one (target, type)."""
    rows = []
    offset = 0
    url0 = None
    while True:
        q = urllib.parse.urlencode({
            'target_chembl_id': tid,
            'standard_type': atype,
            'limit': PAGE,
            'offset': offset,
            'only': ','.join([
                'activity_id', 'molecule_chembl_id', 'canonical_smiles',
                'standard_type', 'standard_relation', 'standard_value',
                'standard_units', 'pchembl_value', 'assay_chembl_id',
                'target_chembl_id', 'document_chembl_id',
            ]),
        })
        url = CHEMBL + '?' + q
        if url0 is None:
            url0 = url
        payload = get_json(url)
        acts = payload.get('activities') or []
        for a in acts:
            pv = a.get('pchembl_value')
            smi = a.get('canonical_smiles')
            if not pv or not smi or not a.get('standard_value'):
                continue
            try:
                pv = float(pv)
            except (TypeError, ValueError):
                continue
            # Keep a biologically sane affinity window.
            if not (2.0 <= pv <= 13.0):
                continue
            rows.append({
                'gene': gene,
                'target_chembl_id': tid,
                'activity_id': a.get('activity_id'),
                'molecule_chembl_id': a.get('molecule_chembl_id'),
                'smiles': smi,
                'standard_type': atype,
                'standard_relation': a.get('standard_relation'),
                'standard_value_nM': a.get('standard_value'),
                'standard_units': a.get('standard_units'),
                'pchembl_value': pv,
                'assay_chembl_id': a.get('assay_chembl_id'),
                'document_chembl_id': a.get('document_chembl_id'),
                'source': 'ChEMBL',
                'retrieved_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            })
        total = payload.get('page_meta', {}).get('total_count', 0)
        offset += PAGE
        print('    %s %-5s offset=%-6d kept_so_far=%d / total=%d' % (gene, atype, offset, len(rows), total), flush=True)
        if offset >= total or not acts:
            break
        time.sleep(0.35)
    return rows, url0


def fetch_fasta(acc):
    req = urllib.request.Request(UNIPROT.format(acc=acc), headers=UA)
    with urllib.request.urlopen(req, timeout=90) as fh:
        txt = fh.read().decode('utf-8')
    seq = ''.join(line.strip() for line in txt.splitlines() if not line.startswith('>'))
    header = next((line for line in txt.splitlines() if line.startswith('>')), '')
    return seq, header


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    manifest = {
        'purpose': 'REAL measured data for the MEG-BAR empirical study (no simulation)',
        'retrieved_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'chembl_base': CHEMBL,
        'activity_types': ACTIVITY_TYPES,
        'page_size': PAGE,
        'targets': {},
        'queries': [],
    }

    all_rows = []
    for gene, tid, acc, name in TARGETS:
        print('[*] %s (%s)' % (gene, tid), flush=True)
        per_gene = {}
        for atype in ACTIVITY_TYPES:
            rows, url = fetch_target(gene, tid, atype)
            manifest['queries'].append({'gene': gene, 'target': tid, 'type': atype, 'first_url': url})
            per_gene[atype] = len(rows)
            all_rows.extend(rows)
        manifest['targets'][gene] = {
            'chembl_target_id': tid,
            'uniprot': acc,
            'name': name,
            'records_per_type': per_gene,
            'records_total': sum(per_gene.values()),
        }

    csv_path = os.path.join(OUT, 'raw_activities.csv')
    fields = list(all_rows[0].keys())
    with io.open(csv_path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)
    print('[*] wrote %s (%d rows)' % (csv_path, len(all_rows)), flush=True)

    print('[*] fetching UniProt sequences', flush=True)
    proteins = {}
    for gene, tid, acc, name in TARGETS:
        seq, header = fetch_fasta(acc)
        proteins[gene] = {
            'accession': acc,
            'name': name,
            'chembl_target_id': tid,
            'uniprot_header': header,
            'length': len(seq),
            'sequence': seq,
        }
        print('    %-8s %s  len=%d' % (gene, acc, len(seq)), flush=True)
        time.sleep(0.5)

    prot_path = os.path.join(OUT, 'proteins.json')
    with io.open(prot_path, 'w', encoding='utf-8') as fh:
        json.dump(proteins, fh, indent=2)
    print('[*] wrote %s' % prot_path, flush=True)

    manifest['row_count'] = len(all_rows)
    manifest['artifact_sha256'] = {
        'raw_activities.csv': sha256(csv_path),
        'proteins.json': sha256(prot_path),
    }
    with io.open(os.path.join(OUT, 'fetch_manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2)

    print('\n=== SUMMARY ===')
    tot = 0
    for g in manifest['targets']:
        t = manifest['targets'][g]
        print('  %-8s %-12s %s' % (g, t['chembl_target_id'], t['records_per_type']))
        tot += t['records_total']
    print('  TOTAL measured records: %d' % tot)
    for g in proteins:
        print('  %-8s sequence length %d' % (g, proteins[g]['length']))


if __name__ == '__main__':
    sys.exit(main())
