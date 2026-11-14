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

import numpy as np
from scipy import stats

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


def supported(ev):
    return bool(ev and ev.get('wilcoxon_p', 1.0) < ALPHA
                and ev.get('mean_diff', 0) > 0)


def paired_pooled(store, a, b):
    """Paired per-seed differences a-b pooled across receptors, with the
    same Wilcoxon + bootstrap summary as Phase 25."""
    pooled = []
    for key in sorted(k for k in store if k.startswith('E3|')):
        x = store[key].get(a, {})
        y = store[key].get(b, {})
        if 'seeds' not in x or 'seeds' not in y:
            continue
        xs = {s['seed']: s['pearson_r'] for s in x['seeds']}
        ys = {s['seed']: s['pearson_r'] for s in y['seeds']}
        pooled += [xs[s] - ys[s] for s in sorted(xs) if s in ys]
    if not pooled:
        return {}
    arr = np.array(pooled)
    res = {'n_pairs': int(len(arr)),
           'mean_diff': round(float(arr.mean()), 5)}
    if len(arr) >= 5 and np.any(arr != 0):
        try:
            res['wilcoxon_p'] = round(float(stats.wilcoxon(arr).pvalue), 5)
        except ValueError:
            res['wilcoxon_p'] = 1.0
    else:
        res['wilcoxon_p'] = 1.0
    rng = np.random.default_rng(0)
    boots = [arr[rng.integers(0, len(arr), len(arr))].mean() for _ in range(1000)]
    res['bootstrap_ci95'] = [round(float(np.percentile(boots, 2.5)), 5),
                             round(float(np.percentile(boots, 97.5)), 5)]
    return res


def main():
    e3 = load(E3_STORE)
    stats_ = load(os.path.join(ST4, 'statistics.json')) or {}
    af = load(os.path.join(ST5, 'af_results.json'))
    af_comp = load(os.path.join(ST5, 'af_comparison.json'))

    sec = stats_.get('secondary', {})
    prim = stats_.get('primary_endpoint', {}).get('result', {}).get('pooled', {})
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

    # H4: AFDB grounding gives the same QUALITATIVE conclusion as crystal
    # (PREREGISTRATION wording). Operationalisation: run the same paired
    # C-vs-E test on the AF-geometry store; the conclusion transfers iff the
    # verdict (significant vs not at alpha) matches the crystal verdict and,
    # when both are significant, the sign matches. Magnitudes are reported
    # alongside (pooled AF-vs-crystal delta) - sign flips of differences
    # that are noise around zero are NOT a different conclusion.
    h4_supported, h4_evidence = None, {}
    if af:
        af_cve = paired_pooled(af, 'pocket3d', 'pocket3d_wrongpocket')
        crystal_sig = supported(h2)
        af_sig = supported(af_cve)
        same = (af_sig == crystal_sig)
        if same and af_sig:
            same = ((af_cve.get('mean_diff', 0) > 0)
                    == (h2.get('mean_diff', 0) > 0))
        h4_supported = bool(af_cve) and same
        h4_evidence = {
            'af_c_vs_e': af_cve,
            'crystal_c_vs_e': h2,
            'verdict_transfer': same,
            'pooled_af_delta_vs_crystal':
                (af_comp or {}).get('pooled_delta_r_pocket3d'),
        }
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
