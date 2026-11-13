"""Generate the Colab runner notebook for MEG-BAR.

Writes colab/MEGBAR_colab_runner.ipynb in valid nbformat 4.
Run: python scripts/real/_make_colab_nb.py
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "colab", "MEGBAR_colab_runner.ipynb")


def md(text):
    return {"cell_type": "markdown", "metadata": {},
            "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": text.splitlines(keepends=True)}


CELLS = []

CELLS.append(md("""# MEG-BAR — Colab runner

Real measured pipeline. **No simulated numbers.** Every correlation this
notebook produces comes from an executed training run whose JSON is
flushed to disk after each fold.

**Runtime → Change runtime type → T4 GPU** before running.

Upload the PC's `projects/MEG-BAR/colab/` folder to `MyDrive/MEG-BAR/`
so the tree is:

```
MyDrive/MEG-BAR/
  data/      7 files, 14.3 MB
  scripts/   8 .py files
  results/   previous JSONs
```
"""))

CELLS.append(md("## 1. Mount Drive and verify the payload"))

CELLS.append(code("""from google.colab import drive
drive.mount('/content/drive')

import os
BASE = '/content/drive/MyDrive/MEG-BAR'
assert os.path.isdir(BASE), f'{BASE} missing - upload the colab/ folder there'

for sub in ('data', 'scripts', 'results'):
    p = os.path.join(BASE, sub)
    n = len(os.listdir(p)) if os.path.isdir(p) else 0
    print(f'{sub:8s} {n:3d} files')
    assert n > 0, f'{sub} is empty'

# size floors: a truncated .npz loads as a smaller array and silently
# corrupts every downstream number, so check before trusting anything
need = {'raw_activities.csv': 3.5e6, 'ligand_fp_cache.npz': 1.5e6,
        'residue_embeddings.npz': 7e6}
for f, floor in need.items():
    fp = os.path.join(BASE, 'data', f)
    sz = os.path.getsize(fp)
    print(f'  {f:26s} {sz/1e6:7.2f} MB')
    assert sz > floor, f'{f} looks truncated'

print('\\npayload OK')
"""))

CELLS.append(md("""## 2. Stage and run

Staging to `/content` (local SSD) instead of training off Drive avoids
slow network I/O racing the per-fold JSON flushes. `results/` is copied
in so `08_robust_eval.py` can skip folds it already finished.""" ))

CELLS.append(code("""import os, sys, shutil, subprocess, torch

print('CUDA:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
else:
    print('WARNING: no GPU - this takes ~10 hours. '
          'Runtime > Change runtime type > T4 GPU.')

BASE = '/content/drive/MyDrive/MEG-BAR'
RUN = '/content/megbar_run'

if os.path.isdir(RUN):
    shutil.rmtree(RUN)
for sub in ('scripts/real', 'data/real'):
    os.makedirs(f'{RUN}/{sub}', exist_ok=True)

for f in os.listdir(f'{BASE}/scripts'):
    if f.endswith('.py'):
        shutil.copy(f'{BASE}/scripts/{f}', f'{RUN}/scripts/real/{f}')
for f in os.listdir(f'{BASE}/data'):
    shutil.copy(f'{BASE}/data/{f}', f'{RUN}/data/real/{f}')
for f in os.listdir(f'{BASE}/results'):
    shutil.copy(f'{BASE}/results/{f}', f'{RUN}/data/real/{f}')

n_scripts = len(os.listdir(RUN + '/scripts/real'))
n_data = len(os.listdir(RUN + '/data/real'))
print(f'staged {n_scripts} scripts, {n_data} data files\\n', flush=True)

env = dict(os.environ, PYTHONIOENCODING='utf-8')
rc = subprocess.run([sys.executable, 'scripts/real/08_robust_eval.py'],
                    cwd=RUN, env=env).returncode
print('\\nexit code:', rc)

for f in ('robust_results.json', 'robust_report.md'):
    src = f'{RUN}/data/real/{f}'
    if os.path.exists(src):
        shutil.copy(src, f'{BASE}/results/{f}')
        print('saved to Drive:', f)
    else:
        print('MISSING (run did not finish):', src)
"""))

CELLS.append(md("## 3. Read the results"))

CELLS.append(code("""import json
BASE = '/content/drive/MyDrive/MEG-BAR'
d = json.load(open(f'{BASE}/results/robust_results.json', encoding='utf-8'))

ARCHS = ['ridge', 'shared', 'crossattn', 'crossattn_wrongpocket']
hdr = 'block' + ' ' * 7 + ' '.join(f'{a[:12]:>13s}' for a in ARCHS) + '   wilcoxon p'
print(hdr)
print('-' * len(hdr))
for key in sorted(k for k in d if '|' in k):
    b = d[key]
    cells = []
    for a in ARCHS:
        r = b.get(a) or {}
        if 'skipped' in r:
            cells.append(f'{"SKIP":>13s}')
        elif 'mean_r' in r:
            cells.append(f'{r["mean_r"]:6.3f}+-{r["sd_r"]:.3f}')
        elif 'pearson_r' in r:
            cells.append(f'{r["pearson_r"]:13.3f}')
        else:
            cells.append(f'{"-":>13s}')
    w = b.get('wilcoxon_crossattn_vs_shared', {})
    p = f'{w["pvalue"]:.4f}' if 'pvalue' in w else '-'
    print(f'{key:12s} ' + ' '.join(cells) + f'   {p:>10s}')
"""))

CELLS.append(md("""## 4. Two results that are supposed to look wrong

**`E3|GABRA1` shows `crossattn SKIP`.** Deliberate `MIN_TRAIN=800` guard.
GABA-A α1 has 331 molecules total (216 in the E3 train split). In the
earlier run the attention model *diverged* there (r = −0.170,
RMSE 5.308). The guard is the fix, not a failure.

**`crossattn_wrongpocket` matches or beats `crossattn`.** This arm feeds a
*different receptor's* pocket to the identical architecture. If the gain
came from real receptor-pocket information, it should collapse. It does
not. That is the finding: the improvement over the `shared` baseline
tracks added capacity plus the attention mechanism, not receptor
conditioning. Do not "fix" this — report it.
"""))

CELLS.append(md("""## 5. Reference: measured locally 2026-11-12

Scaffold-disjoint within-receptor, 5 seeds, mean Pearson r:

| Receptor | n_train | ridge | shared | crossattn | wrong-pocket | p |
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
*worse*. The Colab run exists to finish E4 across the remaining
receptors on GPU.
"""))

NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
        "colab": {"provenance": [], "gpuType": "T4"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(NOTEBOOK, fh, ensure_ascii=False, indent=1)
    # round-trip validate
    with io.open(OUT, encoding="utf-8") as fh:
        chk = json.load(fh)
    assert chk["nbformat"] == 4
    assert len(chk["cells"]) == len(CELLS)
    for c in chk["cells"]:
        assert c["cell_type"] in ("markdown", "code")
        assert isinstance(c["source"], list) and c["source"]
    n_code = sum(1 for c in chk["cells"] if c["cell_type"] == "code")
    print("wrote", OUT)
    print("cells:", len(chk["cells"]), f"({n_code} code)")
    print("bytes:", os.path.getsize(OUT))


if __name__ == "__main__":
    main()
