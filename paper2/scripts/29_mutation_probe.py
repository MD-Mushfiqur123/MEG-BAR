#!/usr/bin/env python3
"""Phase 29 - mutation probe (time-boxed, honest not-run if infeasible).

Plan question: do 2-3 known point mutations with measured affinity shifts
let 3D grounding respond where 1D cannot? Requirement: mutant-specific
bioactivity records (assay descriptions naming a mutation) in the FROZEN
ChEMBL artefacts. Zero-simulation rule: if the frozen artefacts do not
carry mutation-identifying fields, the probe is recorded as not-run - no
re-downloading, no fabrication.

Run:  python3 paper2/scripts/29_mutation_probe.py
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT_DIR = os.path.join(REPO, 'paper2', 'results', 'stage5')

RAW = os.path.join(REPO, 'data', 'real', 'raw_activities_expanded.csv')
KEYWORDS = ('mutant', 'mutation', 'point mutant')
COLUMNS_NEEDED = {'assay_description'}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    report = {
        'phase': 29,
        'question': ('Do known point mutations with measured affinity shifts '
                     'let 3D pocket grounding respond where 1D cannot?'),
        'status': 'not-run',
        'reason': None,
        'evidence': {},
    }
    if not os.path.exists(RAW):
        report['reason'] = 'frozen artefact data/real/raw_activities_expanded.csv missing'
    else:
        with open(RAW) as fh:
            reader = csv.DictReader(fh)
            cols = set(reader.fieldnames or [])
            missing = COLUMNS_NEEDED - cols
            n_rows = 0
            hits = 0
            if not missing:
                for row in reader:
                    n_rows += 1
                    desc = (row.get('assay_description') or '').lower()
                    if any(k in desc for k in KEYWORDS):
                        hits += 1
            report['evidence'] = {
                'columns': sorted(cols),
                'missing_columns': sorted(missing),
                'n_activity_rows': n_rows,
                'n_mutation_keyword_rows': hits,
            }
            if missing:
                report['reason'] = (
                    'frozen ChEMBL artefact has no assay_description column; '
                    'mutant-specific records cannot be identified without '
                    're-downloading (forbidden by the frozen-data rule)')
            elif hits == 0:
                report['reason'] = ('no assay description in the frozen '
                                    'artefact mentions a mutation')
    out = os.path.join(OUT_DIR, 'mutation_probe.json')
    with open(out, 'w') as fh:
        json.dump(report, fh, indent=1)
    print('[OK] Phase 29 status=%s -> %s'
          % (report['status'], os.path.relpath(out, REPO)))
    if report['reason']:
        print('     reason: %s' % report['reason'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
