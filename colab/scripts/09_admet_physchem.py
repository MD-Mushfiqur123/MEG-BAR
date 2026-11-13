#!/usr/bin/env python3
"""09_admet_physchem.py — Phase 2: real computed physicochemistry, replacing hardcoded ADMET constants.

Computes, with RDKit, on every unique molecule in data/real/raw_activities.csv:
  MW, cLogP (Crippen), TPSA, HBD, HBA, rotatable bonds, aromatic rings.

CNS-MPO: Wager et al. 2010 desirability functions at the published inflection
points, implemented in code (piecewise-linear between d=1.0 and d=0.0):
  cLogP  monotonic  d=1 at <=3, d=0 at >=5
  MW     monotonic  d=1 at <=360, d=0 at >=500
  HBD    monotonic  d=1 at <=0.5, d=0 at >=3.5
  TPSA   hump       d=0 below 20, d=1 on [40, 90], d=0 above 120
The cLogD and pKa terms of the published six-parameter score are OMITTED:
no reproducibly computable pKa predictor is available in this environment, and
typing a constant would repeat the fabrication this phase exists to remove.
The result is reported as CNS-MPO(4) on a 0-4 scale and is explicitly labelled
as such wherever it appears.

Outputs (data/real/):
  admet_molecules.csv   one row per unique molecule with all descriptors
  admet_physchem.json   summary statistics (overall + per receptor)
"""
import csv
import io
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors

RDLogger.DisableLog('rdApp.*')

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'data', 'real'))


def monotonic(value, d1_at, d0_at):
    """Wager-style monotonic desirability, piecewise-linear between inflection points."""
    if value <= d1_at:
        return 1.0
    if value >= d0_at:
        return 0.0
    return 1.0 - (value - d1_at) / (d0_at - d1_at)


def hump(value, rise0, rise1, fall1, fall0):
    """Wager-style hump desirability (e.g. TPSA)."""
    if value <= rise0 or value >= fall0:
        return 0.0
    if value < rise1:
        return (value - rise0) / (rise1 - rise0)
    if value <= fall1:
        return 1.0
    return 1.0 - (value - fall1) / (fall0 - fall1)


def cns_mpo4(mw, clogp, tpsa, hbd):
    return (monotonic(clogp, 3.0, 5.0)
            + monotonic(mw, 360.0, 500.0)
            + monotonic(hbd, 0.5, 3.5)
            + hump(tpsa, 20.0, 40.0, 90.0, 120.0))


def describe(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return {
        'mw': Descriptors.MolWt(mol),
        'clogp': Crippen.MolLogP(mol),
        'tpsa': rdMolDescriptors.CalcTPSA(mol),
        'hbd': Lipinski.NumHDonors(mol),
        'hba': Lipinski.NumHAcceptors(mol),
        'rotb': rdMolDescriptors.CalcNumRotatableBonds(mol),
        'arom_rings': rdMolDescriptors.CalcNumAromaticRings(mol),
    }


def summarize(vals):
    a = np.asarray(vals, dtype=float)
    return {
        'n': int(a.size),
        'mean': float(a.mean()),
        'sd': float(a.std(ddof=1)),
        'median': float(np.median(a)),
        'p25': float(np.percentile(a, 25)),
        'p75': float(np.percentile(a, 75)),
    }


def main():
    src = os.path.join(OUT, 'raw_activities.csv')
    with io.open(src, encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    print('[*] activity rows: %d' % len(rows), flush=True)

    gene_by_smiles = {}
    for r in rows:
        gene_by_smiles.setdefault(r['smiles'], set()).add(r['gene'])
    count_by_smiles = Counter(r['smiles'] for r in rows)

    uniq = sorted(gene_by_smiles)
    print('[*] unique molecules: %d' % len(uniq), flush=True)

    out_rows = []
    failed = 0
    for i, smi in enumerate(uniq):
        d = describe(smi)
        if d is None:
            failed += 1
            continue
        d['smiles'] = smi
        d['n_records'] = count_by_smiles[smi]
        d['receptors'] = ';'.join(sorted(gene_by_smiles[smi]))
        d['cns_mpo4'] = cns_mpo4(d['mw'], d['clogp'], d['tpsa'], d['hbd'])
        out_rows.append(d)
        if (i + 1) % 2000 == 0:
            print('    %d / %d' % (i + 1, len(uniq)), flush=True)

    print('[*] descriptors computed: %d (failed: %d)' % (len(out_rows), failed), flush=True)

    csv_path = os.path.join(OUT, 'admet_molecules.csv')
    fields = ['smiles', 'receptors', 'n_records', 'mw', 'clogp', 'tpsa', 'hbd',
              'hba', 'rotb', 'arom_rings', 'cns_mpo4']
    with io.open(csv_path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for d in out_rows:
            w.writerow({k: d[k] for k in fields})

    mpo = [d['cns_mpo4'] for d in out_rows]
    summary = {
        'purpose': 'Phase 2: computed physicochemistry and CNS-MPO(4) on the actual ChEMBL molecules (no hardcoded constants)',
        'computed_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'source_csv': 'raw_activities.csv',
        'n_activity_rows': len(rows),
        'n_unique_molecules': len(out_rows),
        'n_unparseable': failed,
        'cns_mpo_note': ('Wager et al. 2010 desirability functions at the published inflection points, '
                         'piecewise-linear, implemented in code. The cLogD and pKa terms of the six-parameter '
                         'score are omitted (no reproducible pKa predictor available); the score is therefore '
                         'labelled CNS-MPO(4) on a 0-4 scale, not CNS-MPO/6.'),
        'desirability_points': {
            'cLogP': {'d=1 at': '<=3', 'd=0 at': '>=5'},
            'MW': {'d=1 at': '<=360', 'd=0 at': '>=500'},
            'HBD': {'d=1 at': '<=0.5', 'd=0 at': '>=3.5'},
            'TPSA': {'d=0 below': 20, 'd=1 on': [40, 90], 'd=0 above': 120},
        },
        'overall': {
            'mw': summarize([d['mw'] for d in out_rows]),
            'clogp': summarize([d['clogp'] for d in out_rows]),
            'tpsa': summarize([d['tpsa'] for d in out_rows]),
            'hbd': summarize([d['hbd'] for d in out_rows]),
            'hba': summarize([d['hba'] for d in out_rows]),
            'rotb': summarize([d['rotb'] for d in out_rows]),
            'arom_rings': summarize([d['arom_rings'] for d in out_rows]),
            'cns_mpo4': summarize(mpo),
            'cns_mpo4_ge_3': float(np.mean([v >= 3.0 for v in mpo])),
            'cns_mpo4_eq_4': float(np.mean([v >= 4.0 for v in mpo])),
            'veber_pass': float(np.mean([(d['tpsa'] <= 140.0 and d['rotb'] <= 10) for d in out_rows])),
            'lipinski_pass': float(np.mean([(d['mw'] <= 500.0 and d['clogp'] <= 5.0
                                             and d['hbd'] <= 5 and d['hba'] <= 10) for d in out_rows])),
        },
        'per_receptor': {},
    }

    for gene in sorted({g for d in out_rows for g in d['receptors'].split(';')}):
        sub = [d for d in out_rows if gene in d['receptors'].split(';')]
        summary['per_receptor'][gene] = {
            'n_molecules': len(sub),
            'cns_mpo4': summarize([d['cns_mpo4'] for d in sub]),
            'clogp': summarize([d['clogp'] for d in sub]),
            'tpsa': summarize([d['tpsa'] for d in sub]),
        }

    json_path = os.path.join(OUT, 'admet_physchem.json')
    with io.open(json_path, 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2)

    print('[*] wrote %s' % json_path, flush=True)
    ov = summary['overall']
    print('\n=== SUMMARY ===')
    print('  molecules          : %d' % ov['cns_mpo4']['n'])
    print('  CNS-MPO(4) mean    : %.3f +/- %.3f (median %.3f)' % (
        ov['cns_mpo4']['mean'], ov['cns_mpo4']['sd'], ov['cns_mpo4']['median']))
    print('  CNS-MPO(4) >= 3.0  : %.1f%%' % (100 * ov['cns_mpo4_ge_3']))
    print('  CNS-MPO(4) = 4.0   : %.1f%%' % (100 * ov['cns_mpo4_eq_4']))
    print('  Veber pass         : %.1f%%' % (100 * ov['veber_pass']))
    print('  Lipinski pass      : %.1f%%' % (100 * ov['lipinski_pass']))
    print('  cLogP mean         : %.2f +/- %.2f' % (ov['clogp']['mean'], ov['clogp']['sd']))
    print('  TPSA mean          : %.1f +/- %.1f' % (ov['tpsa']['mean'], ov['tpsa']['sd']))


if __name__ == '__main__':
    sys.exit(main())
