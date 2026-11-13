import json

P = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\data\large_scale_benchmark_results.json'
d = json.load(open(P, encoding='utf-8'))
ov = d['overall_evaluation']
pf = d['per_family_evaluation']
MODELS = ['ESM-2 (650M) Linear Probe', 'AutoDock-GPU', 'DiffDock', 'MEG-BAR (Ours)']


def r(model, store):
    return store[model]['deterministic_metrics']['pearson_r']


meg, dif, esm, ad = (r('MEG-BAR (Ours)', ov), r('DiffDock', ov),
                     r('ESM-2 (650M) Linear Probe', ov), r('AutoDock-GPU', ov))

print('OVERALL (n=1000):')
for n, v in [('ESM-2', esm), ('AutoDock', ad), ('DiffDock', dif), ('MEG-BAR', meg)]:
    print('  %-10s r=%.4f' % (n, v))
print('  MEG vs DiffDock : %+.2f%%' % ((meg - dif) / dif * 100))
print('  MEG vs ESM-2    : %+.2f%%' % ((meg - esm) / esm * 100))
print('  MEG vs AutoDock : %+.2f%%' % ((meg - ad) / ad * 100))
print()

fams = list(pf.keys())
mean = {m: sum(r(m, pf[f]) for f in fams) / len(fams) for m in MODELS}
print('PER-FAMILY mean r (average of 5 family r values):')
for m in MODELS:
    print('  %-28s mean r=%.4f' % (m, mean[m]))
print('  MEG vs DiffDock : %+.2f%%' % ((mean['MEG-BAR (Ours)'] - mean['DiffDock']) / mean['DiffDock'] * 100))
print('  MEG vs ESM-2    : %+.2f%%' % ((mean['MEG-BAR (Ours)'] - mean['ESM-2 (650M) Linear Probe']) / mean['ESM-2 (650M) Linear Probe'] * 100))
print()
print('  paper Fig2 caption claims: +17.4% DiffDock, +50.5% ESM-2')
print('  paper abstract claims  : +21.6% DiffDock, +44.0% ESM-2')
print()

# sanity: internal arithmetic the paper states
print('--- stated arithmetic checks ---')
print('0.58M / 650M      = %.5f%% (paper: 0.089%%)' % (0.58 / 650 * 100))
print('238.4 / 3.1       = %.2fx  (paper: 76.9x / 77x)' % (238.4 / 3.1))
print('0.825 - 0.612     = %.3f  (paper Sec7: -0.213 ; Fig8 caption: -0.223)' % (0.825 - 0.612))
print('0.213/0.825       = %.2f%% (paper: 25.8%%)' % (0.213 / 0.825 * 100))
print('11.86/7.42 - 1    = %.2f%% (paper: +59.84%% PPL drift)' % ((11.86 / 7.42 - 1) * 100))
print('0.784 - 0.783     = %.4f (contact map retention)' % (0.784 - 0.783))
print('8.14/7.42 - 1     = %.2f%% (paper: +9.70%% Multi-LoRA drift)' % ((8.14 / 7.42 - 1) * 100))
print('7.45/7.42 - 1     = %.2f%% (paper: +0.04%% MEG-BAR drift)' % ((7.45 / 7.42 - 1) * 100))
print()
print('--- bootstrap CI reported vs JSON ---')
for m in MODELS:
    ci = ov[m]['bootstrap_ci_95']['pearson_r']['ci_95']
    print('  %-28s JSON CI = [%.3f, %.3f]' % (m, ci[0], ci[1]))
