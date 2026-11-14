#!/usr/bin/env python3
"""Phase 33 - figures (300 DPI, regenerable, matplotlib only).

  fig_per_receptor_delta.png   per-receptor delta-r of C vs E/B/F controls (E3)
  fig_temporal_decay.png       E3 vs E5 mean r per receptor (shared + pocket3d)
  fig_crystal_vs_af.png        crystal vs AFDB mean r per receptor (pocket3d)
  fig_radius_sweep.png         pocket3d vs wrong-pocket at 5.0/6.5/8.0 A

Run:  python3 paper2/scripts/33_figures.py
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from stage3_common import REPO as _REPO  # noqa: E402

OUT_DIR = os.path.join(_REPO, 'paper2', 'figures')
ST3 = os.path.join(_REPO, 'paper2', 'results', 'stage3')
ST4 = os.path.join(_REPO, 'paper2', 'results', 'stage4')
ST5 = os.path.join(_REPO, 'paper2', 'results', 'stage5')


def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def genes_of(store, prefix):
    return sorted(k.split('|', 1)[1] for k in store
                  if k.startswith(prefix + '|') and isinstance(store[k], dict)
                  and 'pocket3d' in store[k])


def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print('  wrote %s' % os.path.relpath(path, _REPO))


def fig_per_receptor_delta(e3):
    genes = genes_of(e3, 'E3')

    def mean_r(g, arm):
        blk = e3.get('E3|%s' % g, {}).get(arm, {})
        return blk.get('mean_r') if 'seeds' in blk else None

    controls = [('crossattn_1d', 'C - B (1D conditioning)'),
                ('pocket3d_wrongpocket', 'C - E (wrong pocket)'),
                ('pocket3d_shuffled', 'C - F (shuffled coords)')]
    fig, ax = plt.subplots(figsize=(8, 4))
    y = np.arange(len(genes))
    h = 0.8 / len(controls)
    for ci, (arm, label) in enumerate(controls):
        vals = [(mean_r(g, 'pocket3d') - mean_r(g, arm))
                if mean_r(g, 'pocket3d') is not None and mean_r(g, arm) is not None
                else np.nan for g in genes]
        ax.barh(y + (1 - ci) * h - h / 2, vals, height=h * 0.9, label=label)
    ax.axvline(0, color='k', lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(genes)
    ax.invert_yaxis()
    ax.set_xlabel('Delta Pearson r (scaffold-disjoint, 5-seed mean)')
    ax.set_title('3D-grounded arm vs controls: per-receptor effect')
    ax.legend(loc='lower right', fontsize=8)
    save(fig, 'fig_per_receptor_delta.png')


def fig_temporal_decay(e3, e5):
    def mr(store, key, arm):
        blk = store.get(key, {}).get(arm, {})
        return blk.get('mean_r') if 'seeds' in blk else None

    genes = [g for g in genes_of(e3, 'E3')
             if mr(e3, 'E3|%s' % g, 'shared') is not None
             and mr(e3, 'E3|%s' % g, 'pocket3d') is not None
             and mr(e5, 'E5|%s' % g, 'shared') is not None
             and mr(e5, 'E5|%s' % g, 'pocket3d') is not None]
    if not genes:
        print('  temporal figure skipped (no complete E5 store yet)')
        return
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, arm, title in zip(axes, ('shared', 'pocket3d'),
                              ('Arm A (shared MLP)', 'Arm C (pocket3d)')):
        e3v = [mr(e3, 'E3|%s' % g, arm) for g in genes]
        e5v = [mr(e5, 'E5|%s' % g, arm) for g in genes]
        ax.scatter(e3v, e5v, s=28)
        lim = [min(e3v + e5v) - 0.05, max(e3v + e5v) + 0.05]
        ax.plot(lim, lim, 'k--', lw=0.8)
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_xlabel('scaffold-disjoint r (E3)')
        ax.set_title(title)
    axes[0].set_ylabel('temporal r (E5, train <2015 / test >=2015)')
    fig.suptitle('Split-protocol effect on per-receptor Pearson r')
    save(fig, 'fig_temporal_decay.png')


def fig_crystal_vs_af(af_comp):
    if not af_comp or not af_comp.get('per_receptor'):
        print('  crystal-vs-AF figure skipped (no AF store yet)')
        return
    genes = sorted(af_comp['per_receptor'])
    cr = [af_comp['per_receptor'][g]['pocket3d']['crystal_mean_r'] for g in genes]
    af = [af_comp['per_receptor'][g]['pocket3d']['af_mean_r'] for g in genes]
    fig, ax = plt.subplots(figsize=(5, 5))
    lim = [min(cr + af) - 0.05, max(cr + af) + 0.05]
    ax.plot(lim, lim, 'k--', lw=0.8)
    ax.scatter(cr, af, s=30)
    for g, x, yv in zip(genes, cr, af):
        ax.annotate(g, (x, yv), fontsize=6, xytext=(3, 3),
                    textcoords='offset points')
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel('crystal-geometry mean r (pocket3d)')
    ax.set_ylabel('AFDB-geometry mean r (pocket3d)')
    ax.set_title('Predicted vs crystal pocket geometry (H4)')
    save(fig, 'fig_crystal_vs_af.png')


def fig_radius_sweep(sweep):
    if not sweep or not sweep.get('radii'):
        print('  radius-sweep figure skipped (no sweep store yet)')
        return
    radii, c_means, e_means = [], [], []
    for rkey in ('5', '6.5', '8'):
        if rkey == '6.5':
            with open(os.path.join(ST3, 'arms_scaffold_results.json')) as fh:
                store = json.load(fh)
            pfx = 'E3'
        else:
            if rkey not in sweep['radii']:
                continue
            store = sweep['radii'][rkey]['results']
            pfx = 'R%sp' % rkey.replace('.', '')
        genes = [k for k in store if k.startswith(pfx + '|')
                 and 'seeds' in store[k].get('pocket3d', {})]
        if not genes:
            continue
        radii.append(rkey)
        c_means.append(float(np.mean([store[k]['pocket3d']['mean_r'] for k in genes])))
        e_means.append(float(np.mean([store[k]['pocket3d_wrongpocket']['mean_r']
                                      for k in genes])))
    if not radii:
        print('  radius-sweep figure skipped (no complete radius)')
        return
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(radii, c_means, 'o-', label='pocket3d (true pocket)')
    ax.plot(radii, e_means, 's--', label='wrong-pocket control')
    ax.set_xlabel('pocket definition radius (A)')
    ax.set_ylabel("pooled mean Pearson's r")
    ax.set_title('Is the conclusion stable to the pocket radius?')
    ax.legend()
    save(fig, 'fig_radius_sweep.png')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    e3 = load(os.path.join(ST3, 'arms_scaffold_results.json'))
    e5 = load(os.path.join(ST4, 'temporal_results.json'))
    af_comp = load(os.path.join(ST5, 'af_comparison.json'))
    sweep = load(os.path.join(ST5, 'radius_sweep.json'))
    if e3:
        fig_per_receptor_delta(e3)
        if e5:
            fig_temporal_decay(e3, e5)
    fig_crystal_vs_af(af_comp)
    fig_radius_sweep(sweep)
    print('[OK] Phase 33 complete -> %s' % os.path.relpath(OUT_DIR, _REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
