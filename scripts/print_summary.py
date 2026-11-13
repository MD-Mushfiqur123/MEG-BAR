import json

with open('projects/MEG-BAR/data/large_scale_benchmark_results.json') as f:
    d = json.load(f)

print("=== OVERALL (1,000 Complexes, 1,000 Bootstraps) ===")
for m, v in d['overall_evaluation'].items():
    det = v['deterministic_metrics']
    ci = v['bootstrap_ci_95']
    print(f"\n{m}:")
    print(f"  Pearson r:    {det['pearson_r']:.3f} [{ci['pearson_r']['ci_95'][0]:.3f}, {ci['pearson_r']['ci_95'][1]:.3f}]")
    print(f"  Spearman rho: {det['spearman_rho']:.3f} [{ci['spearman_rho']['ci_95'][0]:.3f}, {ci['spearman_rho']['ci_95'][1]:.3f}]")
    print(f"  RMSE:         {det['rmse']:.3f} [{ci['rmse']['ci_95'][0]:.3f}, {ci['rmse']['ci_95'][1]:.3f}]")
    print(f"  MAE:          {det['mae']:.3f}")
    print(f"  R2:           {det['r_squared']:.3f}")

print("\n=== PER RECEPTOR FAMILY ===")
for fam, fval in d['per_family_evaluation'].items():
    print(f"\n--- {fam} ---")
    for m, v in fval.items():
        det = v['deterministic_metrics']
        ci = v['bootstrap_ci_95']
        print(f"  {m:28s} | r={det['pearson_r']:.3f} [{ci['pearson_r']['ci_95'][0]:.3f}, {ci['pearson_r']['ci_95'][1]:.3f}] | rho={det['spearman_rho']:.3f} | RMSE={det['rmse']:.3f}")
