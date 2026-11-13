import json
import math

P = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\data\large_scale_benchmark_results.json'
K = r'C:\Users\mushfiqur\Desktop\agent\projects\MEG-BAR\data\kinase_resistance_benchmark.json'

d = json.load(open(P, encoding='utf-8'))
ov = d['overall_evaluation']

M = 'MEG-BAR (Ours)'
m_mean = ov[M]['bootstrap_ci_95']['pearson_r']['mean']
m_sd = ov[M]['bootstrap_ci_95']['pearson_r']['std']
print('MEG-BAR bootstrap pearson_r: mean=%.7f sd=%.7f' % (m_mean, m_sd))
print()
print('%-30s %10s %10s %10s %10s' % ('baseline', 'mean', 'sd', 'pooled_d', 'paper_d'))
paper = {'DiffDock': 11.04, 'AutoDock-GPU': 14.82, 'ESM-2 (650M) Linear Probe': 16.21}
for b in ['DiffDock', 'AutoDock-GPU', 'ESM-2 (650M) Linear Probe']:
    b_mean = ov[b]['bootstrap_ci_95']['pearson_r']['mean']
    b_sd = ov[b]['bootstrap_ci_95']['pearson_r']['std']
    pooled = math.sqrt((m_sd ** 2 + b_sd ** 2) / 2.0)
    dd = (m_mean - b_mean) / pooled
    print('%-30s %10.6f %10.6f %10.4f %10s' % (b, b_mean, b_sd, dd, paper[b]))
print()
print('=> Cohen\'s d recomputed as (mean_MEG - mean_base)/sqrt((sd_MEG^2+sd_base^2)/2)')

print()
print('--- kinase benchmark record count ---')
k = json.load(open(K, encoding='utf-8'))
print('top keys:', list(k.keys()))


def count_complexes(obj):
    hits = {}
    for key, val in obj.items():
        if isinstance(val, list):
            hits[key] = len(val)
        elif isinstance(val, dict):
            sub = count_complexes(val)
            for sk, sv in sub.items():
                hits[key + '.' + sk] = sv
    return hits


for kk, vv in sorted(count_complexes(k).items()):
    print('  %-52s %d' % (kk, vv))
