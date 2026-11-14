#!/usr/bin/env python3
"""Phase 31 - negative-result guard: formal H1-H4 verdicts.

Reads the frozen stores and the Phase 25 statistics, applies the
PREREGISTRATION.md decision rules verbatim, and writes the official
verdict file. A null verdict is a finding, never a failure (decision
rule 1); nothing here may reinterpret or re-test an endpoint.

Run:  python3 paper2/scripts/31_negative_result_guard.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from stage3_common import REPO as _REPO  # noqa: E402

ST4 = os.path.join(_REPO, 'paper2', 'results', 'stage4')
ST5 = os.path.join(_REPO, 'paper2', 'results', 'stage5')
E3_STORE = os.path.join(_REPO, 'paper2', 'results', 'stage3',
                        'arms_scaffold_results.json')
ALPHA = 0.05


def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def mean_r(store, key, arm):
    blk = (store or {}).get(key, {}).get(arm, {})
    return blk.get('mean_r')


def supported(ev):
    return bool(ev and ev.get('wilcoxon_p', 1.0) < ALPHA
                and ev.get('mean_diff', 0) > 0)


def main():
    e3 = load(E3_STORE)
    stats = load(os.path.join(ST4, 'statistics.json')) or {}
    af_comp = load(os.path.join(ST5, 'af_comparison.json'))

    sec = stats.get('secondary', {})
    prim = stats.get('primary_endpoint', {}).get('result', {}).get('pooled', {})
    verdicts = {'phase': 31, 'alpha': ALPHA, 'hypotheses': {}}

    h1 = sec.get('C_vs_B_1d', {}).get('pooled', {})
    verdicts['hypotheses']['H1'] = {
        'statement': '3D-grounded model (C/D) > 1D cross-attention (B), E3',
        'evidence': h1, 'supported': supported(h1),
    }
    h2 = prim
    verdicts['hypotheses']['H2'] = {
        'statement': 'C significantly outperforms wrong-pocket-3D (E), E3',
        'evidence': h2, 'supported': supported(h2),
    }
    h3 = sec.get('C_vs_F_shuffled', {}).get('pooled', {})
    verdicts['hypotheses']['H3'] = {
        'statement': 'C outperforms shuffled-coordinate control (F), E3',
        'evidence': h3, 'supported': supported(h3),
    }

    h4_supported, h4_evidence = None, {}
    if af_comp and e3:
        signs_agree, pairs = 0, 0
        for g, row in af_comp.get('per_receptor', {}).items():
            cr_c = mean_r(e3, 'E3|%s' % g, 'pocket3d')
            cr_e = mean_r(e3, 'E3|%s' % g, 'pocket3d_wrongpocket')
            af_c = row['pocket3d']['af_mean_r']
            af_e = row['pocket3d_wrongpocket']['af_mean_r']
            if None in (cr_c, cr_e, af_c, af_e):
                continue
            pairs += 1
            if (cr_c - cr_e) * (af_c - af_e) > 0:
                signs_agree += 1
        h4_evidence = {'n_receptors': pairs, 'sign_agreements': signs_agree,
                       'pooled_af_delta_vs_crystal':
                           af_comp.get('pooled_delta_r_pocket3d')}
        h4_supported = (pairs > 0 and signs_agree >= 0.75 * pairs)
    verdicts['hypotheses']['H4'] = {
        'statement': 'AFDB-predicted structures give the same qualitative '
                     'conclusion as crystal structures',
        'evidence': h4_evidence, 'supported': h4_supported,
    }

    if verdicts['hypotheses']['H2']['supported'] is False:
        verdicts['decision'] = (
            'PREREGISTRATION decision rule 1: H2 not supported -> decisive '
            'negative result. 1D embeddings, 3D geometry, and shuffled controls '
            'are statistically indistinguishable on measured data. Reported as '
            'a finding, not a failure.')
    elif not verdicts['hypotheses']['H3']['supported']:
        verdicts['decision'] = (
            'PREREGISTRATION decision rule 2: H2 supported but H3 not - '
            'residue identity, not geometry, drives the gain.')
    else:
        verdicts['decision'] = 'H2 and H3 both supported; report per plan.'

    os.makedirs(ST5, exist_ok=True)
    out = os.path.join(ST5, 'hypothesis_verdicts.json')
    with open(out, 'w') as fh:
        json.dump(verdicts, fh, indent=1)
    lines = ['# Paper 2 - Formal Hypothesis Verdicts (Phase 31)', '']
    for h, v in verdicts['hypotheses'].items():
        lines.append('- **%s:** %s -> **%s**'
                     % (h, v['statement'],
                        'SUPPORTED' if v['supported'] else 'NOT SUPPORTED'))
    lines += ['', 'Decision: %s' % verdicts['decision'], '']
    with open(os.path.join(ST5, 'hypothesis_verdicts.md'), 'w') as fh:
        fh.write('\n'.join(lines))
    print('[OK] Phase 31 complete -> %s' % os.path.relpath(out, _REPO))
    for h, v in verdicts['hypotheses'].items():
        print('  %s: %s' % (h, 'SUPPORTED' if v['supported'] else 'NOT SUPPORTED'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
