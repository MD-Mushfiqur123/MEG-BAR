#!/usr/bin/env python3
"""10_herg_qsar.py — Phase 2: real hERG liability model, replacing the fabricated safety margin.

Fetches measured hERG (KCNH2, KV11.1, UniProt Q12809) IC50 antagonism data for
human hERG (ChEMBL target CHEMBL240) from the live ChEMBL REST API, then trains
a logistic regression on 2048-bit Morgan fingerprints (radius 2) under a
Bemis-Murcko scaffold-disjoint split. Reports measured ROC-AUC with a bootstrap
confidence interval. No safety-margin claim is made without this model.

Outputs (data/real/):
  raw_herg_activities.csv   the fetched measured records
  herg_results.json         dataset composition + test AUC + bootstrap CI
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

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

RDLogger.DisableLog('rdApp.*')

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))

CHEMBL = 'https://www.ebi.ac.uk/chembl/api/data/activity.json'
HERG_TARGET = 'CHEMBL240'
HERG_UNIPROT = 'Q12809'
PAGE = 1000
UA = {'User-Agent': 'Mozilla/5.0 (MEG-BAR real-data experiment; academic use)'}
FP_BITS, FP_RADIUS = 2048, 2
ACTIVE_PCHEMBL = 5.0
SEED = 0
BOOT = 2000


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


def fetch_herg():
    rows = []
    offset = 0
    url0 = None
    while True:
        q = urllib.parse.urlencode({
            'target_chembl_id': HERG_TARGET,
            'standard_type': 'IC50',
            'limit': PAGE,
            'offset': offset,
            'only': ','.join([
                'activity_id', 'molecule_chembl_id', 'canonical_smiles',
                'standard_type', 'standard_relation', 'standard_value',
                'standard_units', 'pchembl_value', 'assay_chembl_id',
                'document_chembl_id',
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
            if not pv or not smi:
                continue
            try:
                pv = float(pv)
            except (TypeError, ValueError):
                continue
            if not (2.0 <= pv <= 13.0):
                continue
            rows.append({
                'activity_id': a.get('activity_id'),
                'molecule_chembl_id': a.get('molecule_chembl_id'),
                'smiles': smi,
                'pchembl_value': pv,
                'assay_chembl_id': a.get('assay_chembl_id'),
                'document_chembl_id': a.get('document_chembl_id'),
            })
        total = payload.get('page_meta', {}).get('total_count', 0)
        offset += PAGE
        print('    offset=%-7d kept=%d / total=%d' % (offset, len(rows), total), flush=True)
        if offset >= total or not acts:
            break
        time.sleep(0.35)
    return rows, url0


def morgan(smi):
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, FP_RADIUS, nBits=FP_BITS)
    arr = np.zeros((FP_BITS,), dtype=np.float32)
    AllChem.DataStructs.ConvertToNumpyArray(fp, arr)
    return arr


def scaffold_of(smi):
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    try:
        return MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
    except Exception:
        return None


def main():
    os.makedirs(OUT, exist_ok=True)
    print('[*] fetching measured hERG IC50 records from ChEMBL (%s)' % HERG_TARGET, flush=True)
    rows, url0 = fetch_herg()
    print('[*] fetched %d records' % len(rows), flush=True)

    best = {}
    for r in rows:
        mid = r['molecule_chembl_id']
        if mid not in best or r['pchembl_value'] > best[mid]['pchembl_value']:
            best[mid] = r
    mols = sorted(best.values(), key=lambda r: r['molecule_chembl_id'])
    print('[*] unique molecules: %d' % len(mols), flush=True)

    X, y, scafs, kept = [], [], [], []
    for r in mols:
        fp = morgan(r['smiles'])
        sc = scaffold_of(r['smiles'])
        if fp is None or sc is None:
            continue
        X.append(fp)
        y.append(1 if r['pchembl_value'] >= ACTIVE_PCHEMBL else 0)
        scafs.append(sc)
        kept.append(r)
    X = np.asarray(X)
    y = np.asarray(y)
    print('[*] modelled molecules: %d (active %d / inactive %d)' % (
        len(y), int(y.sum()), int((1 - y).sum())), flush=True)

    rng = np.random.RandomState(SEED)
    uniq_scaf = sorted(set(scafs))
    scaf_split = {s: rng.rand() for s in uniq_scaf}
    train_idx = [i for i, s in enumerate(scafs) if scaf_split[s] < 0.8]
    test_idx = [i for i, s in enumerate(scafs) if scaf_split[s] >= 0.8]
    print('[*] scaffold-disjoint split: train %d / test %d molecules (%d scaffolds)' % (
        len(train_idx), len(test_idx), len(uniq_scaf)), flush=True)

    clf = LogisticRegression(max_iter=5000, C=1.0, random_state=SEED)
    clf.fit(X[train_idx], y[train_idx])
    p = clf.predict_proba(X[test_idx])[:, 1]
    yt = y[test_idx]
    auc = roc_auc_score(yt, p)
    pr = average_precision_score(yt, p)

    boots = []
    rng_boot = np.random.RandomState(SEED)
    for _ in range(BOOT):
        idx = rng_boot.randint(0, len(yt), len(yt))
        if len(set(yt[idx])) < 2:
            continue
        boots.append(roc_auc_score(yt[idx], p[idx]))
    ci_lo, ci_hi = np.percentile(boots, [2.5, 97.5])

    csv_path = os.path.join(OUT, 'raw_herg_activities.csv')
    with io.open(csv_path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def sha256(path):
        h = hashlib.sha256()
        with open(path, 'rb') as fh2:
            for chunk in iter(lambda: fh2.read(1 << 20), b''):
                h.update(chunk)
        return h.hexdigest()

    results = {
        'purpose': 'Phase 2: measured hERG liability model (real ChEMBL IC50 data, scaffold-disjoint QSAR)',
        'computed_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'target': {'chembl_id': HERG_TARGET, 'uniprot': HERG_UNIPROT, 'name': 'human ether-a-go-go-related gene (hERG/KCNH2/KV11.1) channel'},
        'query_first_url': url0,
        'activity_definition': 'IC50 antagonism records with pchembl_value in [2, 13]; per molecule the most potent (max pchembl) record is retained',
        'active_definition': 'pchembl_value >= %.1f (IC50 <= 10 uM)' % ACTIVE_PCHEMBL,
        'fingerprint': {'type': 'Morgan', 'nBits': FP_BITS, 'radius': FP_RADIUS},
        'model': 'LogisticRegression (scikit-learn, C=1.0, max_iter=5000), Bemis-Murcko scaffold-disjoint 80/20 split, seed %d' % SEED,
        'n_records_fetched': len(rows),
        'n_unique_molecules': len(mols),
        'n_modelled': int(len(y)),
        'n_active': int(y.sum()),
        'n_inactive': int((1 - y).sum()),
        'n_scaffolds': len(uniq_scaf),
        'n_train': len(train_idx),
        'n_test': len(test_idx),
        'test_active': int(yt.sum()),
        'test_inactive': int((1 - yt).sum()),
        'test_roc_auc': float(auc),
        'test_roc_auc_bootstrap95ci': [float(ci_lo), float(ci_hi)],
        'test_pr_auc': float(pr),
        'n_bootstrap': len(boots),
        'artifact_sha256': {'raw_herg_activities.csv': sha256(csv_path)},
    }
    json_path = os.path.join(OUT, 'herg_results.json')
    with io.open(json_path, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2)

    print('[*] wrote %s' % json_path, flush=True)
    print('\n=== SUMMARY ===')
    print('  molecules modelled : %d (active %d)' % (len(y), int(y.sum())))
    print('  test ROC-AUC       : %.3f [%.3f, %.3f]' % (auc, ci_lo, ci_hi))
    print('  test PR-AUC        : %.3f' % pr)


if __name__ == '__main__':
    main()
