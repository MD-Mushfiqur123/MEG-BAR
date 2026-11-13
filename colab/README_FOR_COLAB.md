# MEG-BAR — Google Colab runbook

**What travels:** 14.42 MB total (7 data files, 8 scripts, 4 result JSONs).
**What it produces:** measured scaffold-disjoint and leave-one-receptor-out
correlations for `ridge` / `shared` / `crossattn` / `crossattn_wrongpocket`.
**Wall clock:** ~40 min on a T4 GPU; ~10 h on CPU (the local PC has no GPU).

No simulated numbers anywhere in this pipeline. Every figure written by
`08_robust_eval.py` comes from an executed training run whose JSON output
is flushed to disk after each fold.

---

## 1. Upload

Create this tree in your Drive:

```
MyDrive/MEG-BAR/
├── data/                     # 7 files, 14.3 MB
│   ├── raw_activities.csv            3.88 MB
│   ├── residue_embeddings.npz        8.28 MB
│   ├── ligand_fp_cache.npz           2.07 MB
│   ├── protein_embeddings.npz        0.04 MB
│   ├── pockets.json
│   ├── proteins.json
│   ├── fetch_manifest.json
│   └── residue_manifest.json
├── scripts/                  # 8 .py files
│   ├── 01_fetch_data.py   …   08_robust_eval.py
└── results/                  # previous JSONs (reference + resume)
```

The whole `colab/` folder on the PC is already in this exact layout —
upload that one folder and the paths line up.

---

## 2. Cell 1 — mount and verify

```python
from google.colab import drive
drive.mount('/content/drive')

import os
BASE = '/content/drive/MyDrive/MEG-BAR'
assert os.path.isdir(BASE), f'{BASE} missing — upload the colab/ folder there'

for sub in ('data', 'scripts', 'results'):
    p = os.path.join(BASE, sub)
    n = len(os.listdir(p)) if os.path.isdir(p) else 0
    print(f'{sub:8s} {n:3d} files')
    assert n > 0, f'{sub} is empty'

need = {'raw_activities.csv': 3.5e6, 'ligand_fp_cache.npz': 1.5e6,
        'residue_embeddings.npz': 7e6}
for f, floor in need.items():
    fp = os.path.join(BASE, 'data', f)
    sz = os.path.getsize(fp)
    print(f'  {f:26s} {sz/1e6:7.2f} MB')
    assert sz > floor, f'{f} looks truncated'

print('\npayload OK')
```

The size assertions matter: a truncated `.npz` will silently load as a
smaller array and corrupt every downstream number.

---

## 3. Cell 2 — run

```python
import os, sys, shutil, subprocess, torch

print('CUDA:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
else:
    print('WARNING: no GPU — this will take ~10 hours. '
          'Runtime > Change runtime type > T4 GPU.')

BASE = '/content/drive/MyDrive/MEG-BAR'
RUN  = '/content/megbar_run'

# stage into Colab-local disk: Drive I/O during training is slow and
# the run is resumable only if the JSON writes are not racing the network
if os.path.isdir(RUN):
    shutil.rmtree(RUN)
for sub in ('scripts/real', 'data/real'):
    os.makedirs(f'{RUN}/{sub}', exist_ok=True)

for f in os.listdir(f'{BASE}/scripts'):
    if f.endswith('.py'):
        shutil.copy(f'{BASE}/scripts/{f}', f'{RUN}/scripts/real/{f}')
for f in os.listdir(f'{BASE}/data'):
    shutil.copy(f'{BASE}/data/{f}', f'{RUN}/data/real/{f}')
# seed the resume state so already-finished folds are not recomputed
for f in os.listdir(f'{BASE}/results'):
    shutil.copy(f'{BASE}/results/{f}', f'{RUN}/data/real/{f}')

print(f'staged {len(os.listdir(f"{RUN}/scripts/real"))} scripts, '
      f'{len(os.listdir(f"{RUN}/data/real"))} data files\n', flush=True)

env = dict(os.environ, PYTHONIOENCODING='utf-8')
subprocess.run([sys.executable, 'scripts/real/08_robust_eval.py'],
               cwd=RUN, env=env)

for f in ('robust_results.json', 'robust_report.md'):
    src = f'{RUN}/data/real/{f}'
    if os.path.exists(src):
        shutil.copy(src, f'{BASE}/results/{f}')
        print('saved to Drive:', f)
    else:
        print('MISSING (run did not reach the end):', src)
```

`08_robust_eval.py` is idempotent: it reads any existing
`robust_results.json`, skips folds already present, and only computes what
is missing. Copying `results/` in step 2 is what makes a re-run cheap.

### Two resume bugs fixed 2026-11-12 (use the shipped script, not an older copy)

Both were found by re-running the script against a fully-populated
`robust_results.json`, which is exactly what this notebook does.

1. **`UnboundLocalError: pred`** — a block whose seeds were all already
   done ran no training, so `pred` was never assigned, and the bootstrap
   below it crashed. Since the shipped `results/` has every E3 block
   complete, an unfixed copy crashes on the *first* block. Fixed by
   resetting `pred = None` per architecture and only recomputing the CI
   when a seed actually ran; a resumed block keeps the CI stored by the
   run that did the training.
2. **E4 partial-block skip** — the leave-one-receptor-out guard tested
   only `shared.mean_r`, which is set as soon as the cheapest arm
   finishes. An interrupted E4 block therefore looked complete and its
   remaining arms were silently skipped, leaving `crossattn_wrongpocket`
   averaged over 2 seeds instead of 5. Fixed with `block_complete()`,
   which requires every arch to be either skipped or hold all 5 seeds.

Verified: with the shipped JSON the fixed script skips all four E3 blocks
with zero retraining, preserves their `bootstrap_ci`, and resumes
`E4|CHRM1` at `crossattn_wrongpocket seed=2`.

---

## 4. Cell 3 — read the numbers

```python
import json
BASE = '/content/drive/MyDrive/MEG-BAR'
d = json.load(open(f'{BASE}/results/robust_results.json', encoding='utf-8'))

ARCHS = ['ridge', 'shared', 'crossattn', 'crossattn_wrongpocket']
hdr = f'{"block":12s} ' + ' '.join(f'{a[:12]:>13s}' for a in ARCHS) + '   wilcoxon p'
print(hdr); print('-' * len(hdr))
for key in sorted(k for k in d if '|' in k):
    b = d[key]
    cells = []
    for a in ARCHS:
        r = b.get(a) or {}
        if 'skipped' in r:        cells.append(f'{"SKIP":>13s}')
        elif 'mean_r' in r:       cells.append(f'{r["mean_r"]:6.3f}±{r["sd_r"]:.3f}')
        elif 'pearson_r' in r:    cells.append(f'{r["pearson_r"]:13.3f}')
        else:                     cells.append(f'{"-":>13s}')
    w = b.get('wilcoxon_crossattn_vs_shared', {})
    p = f'{w["pvalue"]:.4f}' if 'pvalue' in w else '-'
    print(f'{key:12s} ' + ' '.join(cells) + f'   {p:>10s}')
```

---

## 5. Two results that are supposed to look wrong

**`GABRA1` shows `crossattn SKIP`.** That is the deliberate
`MIN_TRAIN=800` guard. GABA-A α1 has only 331 molecules (216 in the E3
train split); in the earlier run the attention model **diverged** there
(r = −0.170, RMSE 5.308). The guard is a fix, not a failure.

**`crossattn_wrongpocket` matches or beats `crossattn`.** The wrong-pocket
arm feeds a *different receptor's* pocket to the same architecture. If the
gain came from real receptor-pocket information, this arm should collapse.
It does not. That is the study's actual finding: the improvement over the
`shared` baseline tracks added capacity and the attention mechanism itself,
not receptor conditioning. Do not "fix" this — report it.

---

## 6. Local reference state (measured, 2026-11-12)

Scaffold-disjoint within-receptor, 5 seeds, mean Pearson r:

| Receptor | n_train | ridge | shared | crossattn | wrong-pocket | Wilcoxon p |
|---|---|---|---|---|---|---|
| 5-HT2A | 3715 | 0.597 | 0.660 ± 0.010 | 0.677 ± 0.010 | **0.688 ± 0.006** | 0.1875 |
| D2 | — | 0.521 | 0.577 ± 0.015 | 0.606 ± 0.024 | **0.624 ± 0.013** | 0.0625 |
| M1 | — | 0.546 | **0.559 ± 0.022** | 0.527 ± 0.167 | 0.447 ± 0.204 | 0.6250 |
| GABA-A α1 | 216 | **0.532** | 0.008 ± 0.005 | skipped | skipped | — |

Leave-one-receptor-out, held-out M1 (n_train = 12856):

| arm | mean r |
|---|---|
| shared | **0.168 ± 0.015** |
| crossattn | 0.114 ± 0.036 |
| crossattn_wrongpocket | 0.124 (partial) |

Cross-receptor transfer is weak for every arm, and conditioning makes it
*worse*, not better.
