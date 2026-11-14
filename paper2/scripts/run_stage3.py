"""Stage 3 orchestrator - runs Paper 2 model arms (Phases 16-21) in order.

Executes: 16 (Arm A shared+ridge, regression guard) -> 17 (Arm B 1D
cross-attention) -> 18 (Arm C 3D pocket-graph) -> 19 (Arm D distance-bias)
-> 20 (Arm E wrong-pocket-3D control) -> 21 (Arm F shuffled-coordinates
control), then writes the Stage 3 report.

All arms share one granular-resume store (paper2/results/stage3/
arms_scaffold_results.json): results are flushed after every
(receptor, arm, seed), so an interrupted run resumes exactly where it stopped.
Arms C, E, F are part of the same store and the same commit (non-negotiable 2).

--force deletes the Stage 3 store and reruns every phase from scratch.
Checkpoint state is stored in paper2/results/pipeline_state.json.

Run:  python3 paper2/scripts/run_stage3.py [--force]
"""

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..", "..")
STATE_PATH = os.path.join(REPO, "paper2", "results", "pipeline_state.json")
STORE_PATH = os.path.join(REPO, "paper2", "results", "stage3",
                          "arms_scaffold_results.json")
REPORT_PATH = os.path.join(REPO, "paper2", "results", "stage3",
                           "stage3_report.md")

PHASES = [
    ("16_arm_a_replication", "phase_16_arm_a_replication"),
    ("17_arm_b_1d", "phase_17_arm_b_1d"),
    ("18_arm_c_3d", "phase_18_arm_c_3d"),
    ("19_arm_d_distbias", "phase_19_arm_d_distbias"),
    ("20_arm_e_wrongpocket", "phase_20_arm_e_wrongpocket"),
    ("21_arm_f_shuffled", "phase_21_arm_f_shuffled"),
]

ARMS_ORDER = ["ridge", "shared", "crossattn_1d", "pocket3d", "dist_bias",
              "pocket3d_wrongpocket", "pocket3d_shuffled"]


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"stages": {}}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=1)


def run_script(name):
    script = os.path.join(HERE, f"{name}.py")
    print(f"\n=== running {name}.py ===", flush=True)
    t0 = time.time()
    proc = subprocess.run([sys.executable, script], cwd=REPO)
    dt = time.time() - t0
    if proc.returncode != 0:
        raise SystemExit(f"{name}.py failed (exit {proc.returncode}) after {dt:.1f}s")
    print(f"=== {name}.py OK ({dt:.1f}s) ===", flush=True)
    return dt


def block_complete(blk, arms):
    if not isinstance(blk, dict):
        return False
    for arch in arms:
        a = blk.get(arch)
        if not isinstance(a, dict):
            return False
        if "skipped" in a:
            continue
        if arch == "ridge":
            if "pearson_r" not in a:
                return False
            continue
        if len(a.get("seeds") or []) < 5:
            return False
    return True


def phase_complete(name):
    with open(STORE_PATH, encoding="utf-8") as fh:
        store = json.load(fh)
    arms = {"16_arm_a_replication": ["shared", "ridge"],
            "17_arm_b_1d": ["crossattn_1d"],
            "18_arm_c_3d": ["pocket3d"],
            "19_arm_d_distbias": ["dist_bias"],
            "20_arm_e_wrongpocket": ["pocket3d_wrongpocket"],
            "21_arm_f_shuffled": ["pocket3d_shuffled"]}[name]
    blocks = [v for k, v in store.items() if k.startswith("E3|")]
    if not blocks:
        return False
    return all(block_complete(b, arms) for b in blocks)


def write_report():
    with open(STORE_PATH, encoding="utf-8") as fh:
        store = json.load(fh)
    L = ["# Paper 2 Stage 3 - six model arms, scaffold-disjoint protocol", "",
         "Protocol: Paper 1's exact Bemis-Murcko scaffold-disjoint within-receptor",
         "split, five seeds (0-4), identical optimisation budget (AdamW wd=0.01,",
         "cosine LR peak 5e-4, batch 512, max 70 epochs, patience 7).", "",
         "Arms: `shared` (fingerprint MLP), `ridge` (fingerprint Ridge),",
         "`crossattn_1d` (Paper 1 cross-attention on structure-derived pocket",
         "ESM-2, PCA 1280->128), `pocket3d` (pocket-graph encoder -> cross-attention),",
         "`dist_bias` (distance-biased pocket self-attention -> cross-attention),",
         "`pocket3d_wrongpocket` (Arm C on the WRONG receptor's pocket),",
         "`pocket3d_shuffled` (Arm C with geometry permuted against identity).", "",
         "## Scaffold-disjoint mean Pearson r (5 seeds)", "",
         "| Receptor | " + " | ".join(ARMS_ORDER) + " |",
         "|---|" + "---|" * len(ARMS_ORDER)]
    for key in sorted(k for k in store if k.startswith("E3|")):
        blk = store[key]
        g = key.split("|", 1)[1]
        row = [g]
        for arch in ARMS_ORDER:
            rec = blk.get(arch)
            if not isinstance(rec, dict) or not rec:
                row.append("-")
            elif "skipped" in rec:
                row.append("skipped")
            elif "mean_r" in rec:
                row.append("%.3f±%.3f" % (rec["mean_r"], rec.get("sd_r", 0.0)))
            elif "pearson_r" in rec:
                row.append("%.3f" % rec["pearson_r"])
            else:
                row.append("-")
        L.append("| " + " | ".join(row) + " |")
    guard = store.get("regression_guard")
    if guard:
        L += ["", "## Arm A regression guard vs Paper 1 (shared MLP)", "",
              "Reference: `data/real/expanded_results.json` E3 shared mean_r.",
              "Tolerance ±%.2f. Verdict: **%s** (worst |delta| %.3f)."
              % (guard.get("tolerance", 0), guard.get("verdict"),
                 guard.get("worst_abs_delta", 0)), "",
              "| Receptor | Paper 2 shared r | Paper 1 shared r | |delta| | pass |",
              "|---|---|---|---|---|"]
        for r in guard.get("per_receptor", []):
            L.append("| %s | %.3f | %.3f | %.3f | %s |"
                     % (r["receptor"], r["paper2_shared_mean_r"],
                        r["paper1_shared_mean_r"], r["abs_delta"],
                        "yes" if r["pass"] else "NO"))
    L += ["", "Statistical tests (paired Wilcoxon Arm C vs Arm E, bootstrap CIs,",
          "Holm correction) are Phase 25 (Stage 4) and are deliberately not",
          "computed here.", ""]
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("[OK] wrote %s" % os.path.relpath(REPORT_PATH, REPO), flush=True)


def main():
    force = "--force" in sys.argv
    if force and os.path.exists(STORE_PATH):
        os.remove(STORE_PATH)
        print("[force] deleted Stage 3 store", flush=True)
    state = load_state()
    stages = state.setdefault("stages", {})
    for idx, (name, key) in enumerate(PHASES):
        if (not force and stages.get(key, {}).get("status") == "done"
                and os.path.exists(STORE_PATH) and phase_complete(name)):
            print(f"[skip] {key} (done at {stages[key].get('finished_utc')}; "
                  f"use --force to rerun)")
            continue
        dt = run_script(name)
        stages[key] = {
            "status": "done",
            "script": f"{name}.py",
            "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "runtime_s": round(dt, 1),
        }
        for _, later_key in PHASES[idx + 1:]:
            if stages.get(later_key, {}).get("status") == "done":
                print(f"[invalidate] {later_key} (upstream {key} reran)")
                stages[later_key]["status"] = "stale"
        save_state(state)
    write_report()
    print("\nStage 3 complete. Store:", STORE_PATH)


if __name__ == "__main__":
    main()
