#!/usr/bin/env python3
"""
megbar_cloud.py - ONE-FILE resume runner for the MEG-BAR Phase-1 evaluation.

Designed to run on a cloud GPU (e.g. a Blackwell node with 96 GB VRAM). It has
no dependency beyond the normal scientific stack (numpy, pandas, scipy,
scikit-learn, torch, rdkit) and does NOT need to sit inside the MEG-BAR repo:
you can drop this file anywhere, point it at the project root (or a zip of it),
and it runs.

Usage
-----
    # if the MEG-BAR folder is beside this script:
    python megbar_cloud.py --root ./MEG-BAR

    # if you uploaded a zip of the project (fastest transfer):
    python megbar_cloud.py --zip megbar.zip --unzip-to ./work

    # force GPU (default is CUDA when torch sees one, else CPU):
    python megbar_cloud.py --root ./MEG-BAR --device cuda

It reads data/real/robust_results.json if present, fills ONLY the missing
seeds, and then prints a clean summary table. GPU is preferred automatically.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def run(args):
    root = Path(args.root).resolve()
    eval_script = root / "scripts" / "real" / "08_robust_eval.py"
    if not eval_script.exists():
        sys.exit("[megbar_cloud] 08_robust_eval.py not found under %s" % root)
    results = root / "data" / "real" / "robust_results.json"

    print("=" * 70)
    print("[megbar_cloud] root  =", root)
    print("[megbar_cloud] eval  =", eval_script)
    print("[megbar_cloud] device env =", args.device)

    # Environment for the child evaluator.
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    if args.device:
        env["MEGBAR_DEVICE"] = args.device
    elif "cuda" in torch_string().lower() or cuda_available():
        env["MEGBAR_DEVICE"] = "cuda"
    else:
        env["MEGBAR_DEVICE"] = "cpu"
    env.setdefault("OMP_NUM_THREADS", str(os.cpu_count() or 4))

    # Show current coverage before running.
    if results.exists():
        print("[megbar_cloud] coverage before run:")
        try:
            d = json.load(open(results, encoding="utf-8"))
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
        except Exception as exc:                 # noqa: BLE001
            print("    (could not read coverage:", exc, ")")
    else:
        print("[megbar_cloud] no existing results; fresh evaluation will begin")

    print("[megbar_cloud] launching %s with MEGBAR_DEVICE=%s"
          % (eval_script.name, env["MEGBAR_DEVICE"]))
    r = subprocess.run([sys.executable, str(eval_script)], cwd=str(root), env=env)
    print("[megbar_cloud] evaluator exited with code", r.returncode)
    if r.returncode != 0:
        sys.exit(r.returncode)

    # Print the final summary straight from the artefact.
    if results.exists():
        print("\n[img] FINAL SUMMARY (all values are measured, 5 seeds unless marked ^):")
        d = json.load(open(results, encoding="utf-8"))
        for k in sorted(x for x in d if "|" in x):
            cells = []
            for a in ("shared", "crossattn", "crossattn_wrongpocket"):
                r = d[k].get(a)
                if not r or "skipped" in r:
                    cells.append("    -")
                    continue
                rs = [s["pearson_r"] for s in r.get("seeds", [])]
                if not rs:
                    cells.append("    -")
                    continue
                m = sum(rs) / len(rs)
                mark = "" if len(rs) == 5 else "^"
                cells.append("%7.3f%s" % (m, mark))
            print("    %-12s %s" % (k, "  ".join(cells)))
    return 0


def torch_string():
    try:
        import torch
        return torch.__version__
    except Exception:                            # noqa: BLE001
        return "no-torch"


def cuda_available():
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:                            # noqa: BLE001
        return False


def main():
    ap = argparse.ArgumentParser(description="Resume/run MEG-BAR Phase-1 on a cloud GPU.")
    ap.add_argument("--root", help="Path to the MEG-BAR project root.")
    ap.add_argument("--zip", help="A zip of the MEG-BAR project to unpack first.")
    ap.add_argument("--unzip-to", default="./megbar_work",
                    help="Directory for --zip output (default ./megbar_work).")
    ap.add_argument("--device", choices=["cuda", "cpu", "auto"], default="auto",
                    help="Force MEGBAR_DEVICE. Default: CUDA if torch sees it, else CPU.")
    args = ap.parse_args()

    if args.zip:
        dst = Path(args.unzip_to)
        dst.mkdir(parents=True, exist_ok=True)
        print("[megbar_cloud] unpacking %s -> %s" % (args.zip, dst))
        with zipfile.ZipFile(args.zip) as z:
            z.extractall(dst)
        # A zip commonly contains a top-level folder; find the project root inside.
        cand = [p for p in dst.iterdir() if (p / "scripts").exists()]
        if cand:
            args.root = str(cand[0])
        else:
            args.root = str(dst)
    if not args.root:
        ap.error("--root (or --zip) is required")
    run(args)


if __name__ == "__main__":
    sys.exit(main())