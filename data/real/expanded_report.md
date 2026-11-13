# MEG-BAR — Phase 3 expanded measured evaluation

Eleven receptors (four original + HTR1A, DRD3, ADRA2A, ADRB2, SERT, DAT, HRH1).
Architectures and protocol identical to 08_robust_eval.py; temporal split trains on
pre-2015 records and tests on 2015+ records (document years resolved from ChEMBL).

## E3 — scaffold-disjoint within-receptor

| Split | Arch | mean r | sd | 95% CI | mean rho |
|---|---|---|---|---|---|
| ADRA2A | ridge | 0.800 | - | [0.753, 0.840] | 0.775 |
| ADRA2A | shared | 0.711 | 0.012 | [0.634, 0.756] | 0.766 |
| ADRA2A | crossattn | skipped | - | n_train=667 < MIN_TRAIN=800 | - |
| ADRA2A | crossattn_wrongpocket | skipped | - | n_train=667 < MIN_TRAIN=800 | - |
| ADRB2 | ridge | 0.385 | - | [0.265, 0.492] | 0.325 |
| ADRB2 | shared | 0.541 | 0.013 | [0.426, 0.629] | 0.507 |
| ADRB2 | crossattn | 0.533 | 0.011 | [0.446, 0.632] | 0.496 |
| ADRB2 | crossattn_wrongpocket | 0.529 | 0.014 | [0.422, 0.623] | 0.502 |
| ADRB2 | _Wilcoxon crossattn vs shared_ | p = 0.4375 | | mean diff -0.008 | |
| CHRM1 | ridge | 0.547 | - | [0.471, 0.619] | 0.553 |
| CHRM1 | shared | 0.562 | 0.027 | [0.507, 0.641] | 0.569 |
| CHRM1 | crossattn | 0.523 | 0.164 | [0.539, 0.673] | 0.512 |
| CHRM1 | crossattn_wrongpocket | 0.448 | 0.203 | [0.509, 0.651] | 0.430 |
| CHRM1 | _Wilcoxon crossattn vs shared_ | p = 0.8125 | | mean diff -0.039 | |
| DAT | ridge | 0.607 | - | [0.557, 0.653] | 0.601 |
| DAT | shared | 0.590 | 0.008 | [0.536, 0.639] | 0.549 |
| DAT | crossattn | 0.598 | 0.015 | [0.536, 0.642] | 0.558 |
| DAT | crossattn_wrongpocket | 0.606 | 0.018 | [0.559, 0.660] | 0.561 |
| DAT | _Wilcoxon crossattn vs shared_ | p = 0.4375 | | mean diff +0.008 | |
| DRD2 | ridge | 0.521 | - | [0.487, 0.553] | 0.521 |
| DRD2 | shared | 0.577 | 0.015 | [0.561, 0.625] | 0.570 |
| DRD2 | crossattn | 0.613 | 0.020 | [0.568, 0.630] | 0.606 |
| DRD2 | crossattn_wrongpocket | 0.624 | 0.013 | [0.570, 0.631] | 0.617 |
| DRD2 | _Wilcoxon crossattn vs shared_ | p = 0.1875 | | mean diff +0.036 | |
| DRD3 | ridge | 0.662 | - | [0.623, 0.699] | 0.646 |
| DRD3 | shared | 0.684 | 0.004 | [0.651, 0.722] | 0.669 |
| DRD3 | crossattn | 0.713 | 0.003 | [0.679, 0.743] | 0.696 |
| DRD3 | crossattn_wrongpocket | 0.717 | 0.003 | [0.682, 0.746] | 0.703 |
| DRD3 | _Wilcoxon crossattn vs shared_ | p = 0.0625 | | mean diff +0.029 | |
| GABRA1 | ridge | 0.532 | - | [0.348, 0.701] | 0.459 |
| GABRA1 | shared | 0.008 | 0.005 | [-0.205, 0.196] | -0.103 |
| GABRA1 | crossattn | skipped | - | n_train=216 < MIN_TRAIN=800 | - |
| GABRA1 | crossattn_wrongpocket | skipped | - | n_train=216 < MIN_TRAIN=800 | - |
| HRH1 | ridge | 0.825 | - | [0.780, 0.863] | 0.790 |
| HRH1 | shared | 0.802 | 0.007 | [0.759, 0.836] | 0.777 |
| HRH1 | crossattn | 0.834 | 0.004 | [0.802, 0.865] | 0.797 |
| HRH1 | crossattn_wrongpocket | 0.824 | 0.022 | [0.802, 0.865] | 0.785 |
| HRH1 | _Wilcoxon crossattn vs shared_ | p = 0.0625 | | mean diff +0.032 | |
| HTR1A | ridge | 0.601 | - | [0.567, 0.637] | 0.626 |
| HTR1A | shared | 0.682 | 0.002 | [0.648, 0.715] | 0.680 |
| HTR1A | crossattn | 0.698 | 0.003 | [0.662, 0.727] | 0.694 |
| HTR1A | crossattn_wrongpocket | 0.703 | 0.005 | [0.679, 0.740] | 0.694 |
| HTR1A | _Wilcoxon crossattn vs shared_ | p = 0.0625 | | mean diff +0.016 | |
| HTR2A | ridge | 0.597 | - | [0.557, 0.636] | 0.612 |
| HTR2A | shared | 0.660 | 0.010 | [0.638, 0.702] | 0.692 |
| HTR2A | crossattn | 0.688 | 0.006 | [0.644, 0.706] | 0.718 |
| HTR2A | crossattn_wrongpocket | 0.698 | 0.006 | [0.673, 0.732] | 0.722 |
| HTR2A | _Wilcoxon crossattn vs shared_ | p = 0.0625 | | mean diff +0.028 | |
| SERT | ridge | 0.444 | - | [0.387, 0.499] | 0.453 |
| SERT | shared | 0.500 | 0.003 | [0.462, 0.545] | 0.497 |
| SERT | crossattn | 0.541 | 0.007 | [0.513, 0.593] | 0.541 |
| SERT | crossattn_wrongpocket | 0.542 | 0.010 | [0.513, 0.592] | 0.545 |
| SERT | _Wilcoxon crossattn vs shared_ | p = 0.0625 | | mean diff +0.040 | |

## E5 — temporal split (train pre-2015, test 2015+)

| Split | Arch | mean r | sd | 95% CI | mean rho |
|---|---|---|---|---|---|
| ADRA2A | ridge | 0.064 | - | [-0.089, 0.199] | 0.026 |
| ADRA2A | shared | 0.109 | 0.012 | [-0.037, 0.218] | 0.163 |
| ADRA2A | crossattn | skipped | - | n_train=603 < MIN_TRAIN=800 | - |
| ADRA2A | crossattn_wrongpocket | skipped | - | n_train=603 < MIN_TRAIN=800 | - |
| ADRB2 | ridge | 0.531 | - | [0.457, 0.599] | 0.545 |
| ADRB2 | shared | 0.723 | 0.003 | [0.669, 0.769] | 0.719 |
| ADRB2 | crossattn | skipped | - | n_train=737 < MIN_TRAIN=800 | - |
| ADRB2 | crossattn_wrongpocket | skipped | - | n_train=737 < MIN_TRAIN=800 | - |
| CHRM1 | ridge | 0.256 | - | [0.188, 0.323] | 0.238 |
| CHRM1 | shared | 0.458 | 0.005 | [0.396, 0.510] | 0.443 |
| CHRM1 | crossattn | 0.459 | 0.007 | [0.419, 0.525] | 0.428 |
| CHRM1 | crossattn_wrongpocket | 0.407 | 0.051 | [0.401, 0.508] | 0.362 |
| CHRM1 | _Wilcoxon crossattn vs shared_ | p = 1.0000 | | mean diff +0.001 | |
| DAT | ridge | 0.302 | - | [0.249, 0.352] | 0.287 |
| DAT | shared | 0.379 | 0.010 | [0.324, 0.426] | 0.371 |
| DAT | crossattn | 0.274 | 0.018 | [0.211, 0.325] | 0.247 |
| DAT | crossattn_wrongpocket | 0.280 | 0.012 | [0.233, 0.345] | 0.255 |
| DAT | _Wilcoxon crossattn vs shared_ | p = 0.0625 | | mean diff -0.105 | |
| DRD2 | ridge | 0.429 | - | [0.402, 0.456] | 0.471 |
| DRD2 | shared | 0.474 | 0.002 | [0.450, 0.504] | 0.513 |
| DRD2 | crossattn | 0.478 | 0.008 | [0.453, 0.505] | 0.502 |
| DRD2 | crossattn_wrongpocket | 0.475 | 0.007 | [0.441, 0.493] | 0.500 |
| DRD2 | _Wilcoxon crossattn vs shared_ | p = 0.3125 | | mean diff +0.004 | |
| DRD3 | ridge | 0.380 | - | [0.342, 0.419] | 0.397 |
| DRD3 | shared | 0.468 | 0.004 | [0.429, 0.499] | 0.475 |
| DRD3 | crossattn | 0.474 | 0.023 | [0.419, 0.490] | 0.489 |
| DRD3 | crossattn_wrongpocket | 0.486 | 0.029 | [0.451, 0.519] | 0.497 |
| DRD3 | _Wilcoxon crossattn vs shared_ | p = 0.6250 | | mean diff +0.006 | |
| HRH1 | ridge | 0.182 | - | [0.108, 0.263] | 0.174 |
| HRH1 | shared | 0.204 | 0.007 | [0.134, 0.270] | 0.142 |
| HRH1 | crossattn | 0.332 | 0.015 | [0.257, 0.403] | 0.246 |
| HRH1 | crossattn_wrongpocket | 0.318 | 0.049 | [0.171, 0.298] | 0.261 |
| HRH1 | _Wilcoxon crossattn vs shared_ | p = 0.0625 | | mean diff +0.127 | |
| HTR1A | ridge | 0.436 | - | [0.400, 0.468] | 0.416 |
| HTR1A | shared | 0.425 | 0.016 | [0.364, 0.436] | 0.377 |
| HTR1A | crossattn | 0.462 | 0.011 | [0.437, 0.503] | 0.425 |
| HTR1A | crossattn_wrongpocket | 0.468 | 0.010 | [0.426, 0.492] | 0.429 |
| HTR1A | _Wilcoxon crossattn vs shared_ | p = 0.0625 | | mean diff +0.037 | |
| HTR2A | ridge | 0.271 | - | [0.234, 0.310] | 0.281 |
| HTR2A | shared | 0.384 | 0.015 | [0.366, 0.437] | 0.407 |
| HTR2A | crossattn | 0.420 | 0.007 | [0.393, 0.456] | 0.440 |
| HTR2A | crossattn_wrongpocket | 0.439 | 0.029 | [0.397, 0.462] | 0.455 |
| HTR2A | _Wilcoxon crossattn vs shared_ | p = 0.0625 | | mean diff +0.035 | |
| SERT | ridge | 0.315 | - | [0.264, 0.365] | 0.332 |
| SERT | shared | 0.252 | 0.013 | [0.213, 0.321] | 0.270 |
| SERT | crossattn | 0.299 | 0.021 | [0.230, 0.335] | 0.309 |
| SERT | crossattn_wrongpocket | 0.296 | 0.023 | [0.231, 0.335] | 0.309 |
| SERT | _Wilcoxon crossattn vs shared_ | p = 0.0625 | | mean diff +0.047 | |

Records without a document year (excluded from E5): 544
Wall clock: 10714.5 s
