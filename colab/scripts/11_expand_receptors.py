#!/usr/bin/env python3
"""11_expand_receptors.py — Phase 3: expand the evidence base beyond four receptors.

Adds seven additional human receptors with adequate ChEMBL coverage:
  HTR1A (5-HT1A), DRD3 (D3), ADRA2A (alpha-2A), ADRB2 (beta-2),
  SLC6A4/SERT, SLC6A3/DAT, HRH1 (H1).

Same protocol as 01_fetch_data.py (Ki/IC50/Kd, pchembl 2-13, live ChEMBL REST).
Also resolves publication years for every document in BOTH the original and the
expanded activity tables (needed for the temporal split: train pre-2015, test 2015+).

Note: the planning document listed P23975 for DAT; UniProt confirms P23975 is the
norepinephrine transporter (SLC6A2). Human DAT is Q01959 (SLC6A3) and that is used here.

Outputs (data/real/):
  raw_activities_expanded.csv   original rows + new-receptor rows
  proteins_expanded.json        original proteins + new sequences
  document_years.json           {document_chembl_id: year}
  expand_manifest.json          queries, counts, timestamps, SHA-256
"""
import csv
import hashlib
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))

CHEMBL = 'https://www.ebi.ac.uk/chembl/api/data/activity.json'
DOC_API = 'https://www.ebi.ac.uk/chembl/api/data/document.json'
UNIPROT = 'https://rest.uniprot.org/uniprotkb/{acc}.fasta'

NEW_TARGETS = [
    ('HTR1A',  'CHEMBL214',  'P08908', 'Serotonin 5-HT1A receptor'),
    ('DRD3',   'CHEMBL234',  'P35462', 'Dopamine D3 receptor'),
    ('ADRA2A', 'CHEMBL1867', 'P08913', 'Alpha-2A adrenergic receptor'),
    ('ADRB2',  'CHEMBL210',  'P07550', 'Beta-2 adrenergic receptor'),
    ('SERT',   'CHEMBL228',  'P31645', 'Serotonin transporter (SLC6A4)'),
    ('DAT',    'CHEMBL238',  'Q01959', 'Dopamine transporter (SLC6A3)'),
    ('HRH1',   'CHEMBL231',  'P35367', 'Histamine H1 receptor'),
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
        print('    %s %-5s offset=%-7d kept=%d / total=%d' % (gene, atype, offset, len(rows), total), flush=True)
        if offset >= total or not acts:
            break
        time.sleep(0.35)
    return rows, url0


def fetch_fasta(acc):
    req = urllib.request.Request(UNIPROT.format(acc=acc), headers=UA)
    with urllib.request.urlopen(req, timeout=90) as fh:
        txt = fh.read().decode('utf-8')
    seq = ''.join(line.strip() for line in txt.splitlines() if not line.startswith('>'))
    return seq


def fetch_document_years(doc_ids):
    years = {}
    ids = sorted(doc_ids)
    chunk = 150
    for i in range(0, len(ids), chunk):
        part = ids[i:i + chunk]
        q = urllib.parse.urlencode({
            'document_chembl_id__in': ','.join(part),
            'limit': chunk,
            'only': 'document_chembl_id,year',
        })
        payload = get_json(DOC_API + '?' + q)
        for d in payload.get('documents') or []:
            y = d.get('year')
            if y:
                years[d['document_chembl_id']] = int(y)
        print('    document years: %d / %d resolved' % (len(years), len(ids)), flush=True)
        time.sleep(0.35)
    return years


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = {
        'purpose': 'Phase 3: expand the measured evidence base to eleven human receptors',
        'retrieved_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'chembl_base': CHEMBL,
        'activity_types': ACTIVITY_TYPES,
        'correction': 'Planning document listed P23975 for DAT; UniProt confirms P23975 is SLC6A2 (NET). Human DAT is Q01959 (SLC6A3) and is used here.',
        'targets': {},
        'queries': [],
    }

    orig_path = os.path.join(OUT, 'raw_activities.csv')
    with io.open(orig_path, encoding='utf-8') as fh:
        orig_rows = list(csv.DictReader(fh))
    print('[*] original rows: %d' % len(orig_rows), flush=True)

    new_rows = []
    for gene, tid, acc, name in NEW_TARGETS:
        print('[*] %s (%s)' % (gene, tid), flush=True)
        per_gene = {}
        for atype in ACTIVITY_TYPES:
            rows, url = fetch_target(gene, tid, atype)
            manifest['queries'].append({'gene': gene, 'target': tid, 'type': atype, 'first_url': url})
            per_gene[atype] = len(rows)
            new_rows.extend(rows)
        manifest['targets'][gene] = {
            'chembl_target_id': tid,
            'uniprot': acc,
            'name': name,
            'records_per_type': per_gene,
            'records_total': sum(per_gene.values()),
        }

    fields = list(orig_rows[0].keys())
    all_rows = orig_rows + new_rows
    exp_path = os.path.join(OUT, 'raw_activities_expanded.csv')
    with io.open(exp_path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)
    print('[*] wrote %s (%d rows)' % (exp_path, len(all_rows)), flush=True)

    print('[*] fetching UniProt sequences for new targets', flush=True)
    prot_path = os.path.join(OUT, 'proteins.json')
    proteins = {}
    if os.path.isfile(prot_path):
        with io.open(prot_path, encoding='utf-8') as fh:
            proteins = json.load(fh)
    for gene, tid, acc, name in NEW_TARGETS:
        seq = fetch_fasta(acc)
        proteins[gene] = {
            'accession': acc,
            'name': name,
            'chembl_target_id': tid,
            'length': len(seq),
            'sequence': seq,
        }
        print('    %-8s %s  len=%d' % (gene, acc, len(seq)), flush=True)
        time.sleep(0.5)
    prot_exp_path = os.path.join(OUT, 'proteins_expanded.json')
    with io.open(prot_exp_path, 'w', encoding='utf-8') as fh:
        json.dump(proteins, fh, indent=2)

    print('[*] resolving document years (temporal split)', flush=True)
    doc_ids = {r['document_chembl_id'] for r in all_rows if r.get('document_chembl_id')}
    years = fetch_document_years(doc_ids)
    years_path = os.path.join(OUT, 'document_years.json')
    with io.open(years_path, 'w', encoding='utf-8') as fh:
        json.dump(years, fh, indent=2)
    resolved = len(years)
    print('[*] document years resolved: %d / %d' % (resolved, len(doc_ids)), flush=True)

    manifest['row_count_expanded'] = len(all_rows)
    manifest['new_rows'] = len(new_rows)
    manifest['documents_total'] = len(doc_ids)
    manifest['documents_with_year'] = resolved
    manifest['artifact_sha256'] = {
        'raw_activities_expanded.csv': sha256(exp_path),
        'proteins_expanded.json': sha256(prot_exp_path),
        'document_years.json': sha256(years_path),
    }
    with io.open(os.path.join(OUT, 'expand_manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2)

    print('\n=== SUMMARY ===')
    by_gene = {}
    for r in all_rows:
        by_gene[r['gene']] = by_gene.get(r['gene'], 0) + 1
    for gene in sorted(by_gene):
        print('  %-8s %d' % (gene, by_gene[gene]))
    print('  TOTAL   %d' % sum(by_gene.values()))


if __name__ == '__main__':
    main()
