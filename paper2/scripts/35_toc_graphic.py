#!/usr/bin/env python3
"""Phase 41 - ACS TOC graphic (3.25 x 1.75 in, 300 DPI, regenerable).

Plots the measured primary endpoint: paired C - E (3D arm vs
wrong-pocket-3D control) difference in Pearson r on both protocols,
with bootstrap 95% CIs from the frozen artefacts.

Run:  python3 paper2/scripts/35_toc_graphic.py
"""
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))

OUT = os.path.join(REPO, 'paper2', 'submission', 'toc_graphic.png')

stats = json.load(open(os.path.join(REPO, 'paper2', 'results',
                                    'stage4', 'statistics.json')))
e3 = stats['primary_endpoint']['result']['pooled']
e5 = stats['temporal_protocol']['C_vs_E_wrongpocket']['pooled']

bars = [
    ('Scaffold-disjoint (E3)', e3['mean_diff'], e3['bootstrap_ci95']),
    ('Temporal (E5)', e5['mean_diff'], e5['bootstrap_ci95']),
]

fig, ax = plt.subplots(figsize=(3.25, 1.75), dpi=300)
x = [0, 1]
means = [b[1] for b in bars]
errs = [[m - ci[0] for (_, m, ci) in bars],
        [ci[1] - m for (_, m, ci) in bars]]
ax.bar(x, means, width=0.55, color=['#4878cf', '#d65f5f'], zorder=2)
ax.errorbar(x, means, yerr=errs, fmt='none', ecolor='black',
            elinewidth=0.8, capsize=3, zorder=3)
ax.axhline(0, color='black', lw=0.7, zorder=1)
ax.set_xticks(x)
ax.set_xticklabels([b[0] for b in bars], fontsize=6)
ax.set_ylabel('$\\Delta r$ (3D $-$ wrong-pocket)', fontsize=6)
ax.set_title('True-pocket 3D geometry vs its control:\n'
             'no significant difference',
             fontsize=7, fontweight='bold')
ax.tick_params(labelsize=6)
for spine in ('top', 'right'):
    ax.spines[spine].set_visible(False)
fig.tight_layout(pad=0.3)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=300)
print('wrote %s' % os.path.relpath(OUT, REPO))
