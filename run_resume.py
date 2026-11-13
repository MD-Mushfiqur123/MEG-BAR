#!/usr/bin/env python3
"""run_resume.py - one-shot resume of the MEG-BAR Phase-1 evaluation.

Purpose
-------
The background worker that was filling the Phase-1 table died after
E4|CHRM1 crossattn seed 2. This script resumes 08_robust_eval.py on a fresh
machine. It is deliberately tiny so a reviewer (or you) can run it without
second-guessing what it does.

State that is already durable in robust_results.json:
    E3|CHRM1 / DRD2 / HTR2A   : shared, crossattn, crossattn_wrongpocket = 5/5
    E3|GABRA1                 : shared 5/5; crossattn & wrongpocket SKIPPED
                                 (n_train=216 < MIN_TRAIN=800, a documented guard)
    E4|DRD2                   : shared, crossattn, crossattn_wrongpocket = 5/5
    E4|CHRM1                  : shared 5/5, crossattn 3/5, wrongpocket 5/5
    E4|GABRA1                 : shared 5/5, crossattn 1/5, wrongpocket absent

The evaluator reads that JSON at startup (block_complete() + per-seed
provenance) and runs ONLY the missing seeds. Nothing already complete is
recomputed. On a single fast machine (multi-core or any CUDA GPU) this is the
remaining work:
    E4|CHRM1   crossattn             seeds 3, 4      (~8-10 min each on CPU)
    E4|GABRA1  crossattn             seeds 1-4        (~7-9 min each on CPU)
    E4|GABRA1  crossattn_wrongpocket seeds 0-4        (~2 min each on CPU)

How to run
----------
    python run_resume.py
It sets the CPU thread count, forces DEVICE=cpu, and runs 08_robust_eval.py.
Set MEGBAR_DEVICE=cuda to use a GPU instead (the evaluator is CUDA-aware).

Dependencies (the same list the project already uses):
    numpy, pandas, scipy, scikit-learn, torch, rdkit
    rdkit is needed only for loading; if it is missing the process will fail
    loudly at import. The fingerprints are precomputed in ligand_fp_cache.npz.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE / "scripts" / "real" / "08_robust_eval.py"
OUT = HERE / "data" / "real"

def main():
    if not EVAL.exists():
        sys.exit("08_robust_eval.py not found next to this script: %s" % EVAL)
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    # Force a stable, predictable device unless the user opts into CUDA.
    env.setdefault("MEGBAR_DEVICE", "cuda" if env.get("MEGBAR_DEVICE") == "cuda" else "cpu")
    # Torch thread cap: leave some cores for the OS. Harmless if OMP is ignored.
    env.setdefault("OMP_NUM_THREADS", str(os.cpu_count() or 4))
    print("[run_resume] launching:", EVAL)
    print("[run_resume] device env MEGBAR_DEVICE=", env.get("MEGBAR_DEVICE"))
    print("[run_resume] existing coverage:")
    sj = OUT / "robust_results.json"
    if sj.exists():
        try:
            import json
            d = json.load(open(sj, encoding="utf-8"))
            for k in sorted(x for x in d if "|" in x):
                parts = []
                for a in ("ridge", "shared", "crossattn", "crossattn_wrongpocket"):
                    r = d[k].get(a)
                    if not r:
                        parts.append("%s=-" % a)
                    elif "skipped" in r:
                        parts.append("%s=skip" % a)
                    elif "seeds" in r:
                        parts.append("%s=%d" % (a, len(r["seeds"])))
                    else:
                        parts.append("%s=1" % a)
                print("    %-12s %s" % (k, "  ".join(parts)))
        except Exception as exc:   # noqa: BLE001
            print("    (could not read coverage:", exc, ")")
    # Actually run. This blocks until the evaluation finishes.
    r = subprocess.run([sys.executable, str(EVAL)], cwd=str(HERE), env=env)
    print("[run_resume] evaluator exited with code", r.returncode)
    return r.returncode

if __name__ == "__main__":
    sys.exit(main())